from pathlib import Path
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import models
from core_engines.recon.runner import ReconRunner

async def launch_scan(target_name: str, target_domain: str, target_mode: str, session: Session):
    import asyncio
    import json
    import logging
    from datetime import datetime, timezone
    from core_engines.recon.tools import verify_recon_tools, validate_mode_compatibility

    logger = logging.getLogger("rastro.main")

    # Validate inputs
    if not target_name or not target_name.strip():
        raise HTTPException(status_code=400, detail="Target name is required")
    if not target_domain or not target_domain.strip():
        raise HTTPException(status_code=400, detail="Target domain is required")

    mode = (target_mode or "FAST").upper()
    if mode not in {"FAST", "DEEP", "API"}:
        raise HTTPException(
            status_code=400, detail=f"Invalid mode: {mode}. Use FAST, DEEP, or API"
        )

    # Verify recon tools are available
    logger.info(f"Verifying recon tools for mode {mode}...")
    tool_status = await verify_recon_tools(mode)
    is_compatible, reason = validate_mode_compatibility(mode, tool_status)
    if not is_compatible:
        logger.error(f"Recon tools incompatible: {reason}")
        raise HTTPException(
            status_code=412, detail=f"Recon tools not available: {reason}"
        )

    # Ensure target exists in DB
    db_target = (
        session.query(models.Target).filter(models.Target.name == target_name).first()
    )
    if not db_target:
        db_target = models.Target(name=target_name, domain=target_domain)
        session.add(db_target)
        session.commit()
        session.refresh(db_target)
        logger.info(f"Created target: {target_name}")

    # Create scan run record
    scan = models.ScanRun(target_id=db_target.id, mode=mode, status="running")
    session.add(scan)
    session.commit()
    session.refresh(scan)
    logger.info(f"Started scan run {scan.id} for target {target_name}")

    runner = ReconRunner(Path("./targets") / target_name)
    outputs = {}
    endpoint_count = 0

    try:
        timeout = int(__import__("os").environ.get("SCAN_TIMEOUT", "600"))
        logger.info(f"Running recon pipeline with timeout {timeout}s...")
        outputs = await asyncio.wait_for(
            runner.run_pipeline(target_domain, mode=mode), timeout=timeout
        )
        logger.info("Recon pipeline completed successfully")

        # Persist normalized endpoints into DB
        normalized_path = outputs.get("normalized_endpoints")
        if normalized_path and Path(normalized_path).exists():
            logger.info(f"Parsing normalized endpoints from {normalized_path}")
            try:
                with open(
                    normalized_path, "r", encoding="utf-8", errors="ignore"
                ) as fh:
                    entries = json.load(fh)
                logger.info(f"Found {len(entries)} endpoint entries to persist")

                seen_in_memory = set()

                existing = session.query(models.Endpoint.method, models.Endpoint.path).filter(
                    models.Endpoint.target_id == db_target.id
                ).all()
                db_existing_set = {f"{m}:{p}" for m, p in existing}

                new_endpoints_batch = []

                for entry in entries:
                    try:
                        path = (
                            entry.get("normalized")
                            or entry.get("path")
                            or entry.get("raw")
                        )
                        if not path:
                            logger.warning(f"Skipping entry with no path: {entry}")
                            continue

                        method = entry.get("method", "GET").upper()
                        dup_key = f"{method}:{path}"

                        if dup_key in seen_in_memory:
                            continue

                        if dup_key in db_existing_set:
                            logger.debug(f"Skipping duplicate: {method} {path}")
                            seen_in_memory.add(dup_key)
                            continue

                        # Store metadata as JSON
                        params_meta = {
                            "labels": entry.get("labels", []),
                            "score": entry.get("score", 0),
                            "raw": entry.get("raw"),
                            "host": entry.get("host"),
                            "auth_smells": entry.get("auth_smells", []),
                        }
                        db_ep = models.Endpoint(
                            target_id=db_target.id,
                            path=path,
                            method=method,
                            params=json.dumps(params_meta, ensure_ascii=False),
                        )
                        new_endpoints_batch.append(db_ep)
                        seen_in_memory.add(dup_key)
                        endpoint_count += 1
                    except Exception as ep_exc:
                        logger.warning(f"Error persisting endpoint {entry}: {ep_exc}")
                        continue

                if new_endpoints_batch:
                    session.add_all(new_endpoints_batch)
                session.commit()
                logger.info(f"Persisted {endpoint_count} endpoints to DB")
            except json.JSONDecodeError as json_exc:
                logger.error(f"Failed to parse normalized endpoints JSON: {json_exc}")
                endpoint_count = 0
            except Exception as persist_exc:
                logger.error(f"Error during endpoint persistence: {persist_exc}")
                endpoint_count = 0
        else:
            logger.warning(
                "Normalized endpoints file missing or empty. Skipping persistence."
            )

        # Update scan record with success
        scan.status = "completed"
        scan.finished_at = datetime.now(timezone.utc)
        scan.endpoint_count = endpoint_count
        try:
            scan.outputs = json.dumps(outputs, ensure_ascii=False)
        except Exception as json_exc:
            logger.warning(f"Could not serialize outputs to JSON: {json_exc}")
            scan.outputs = str(outputs)[:500]
        session.add(scan)
        session.commit()
        logger.info(f"Scan {scan.id} completed: {endpoint_count} endpoints")

    except asyncio.TimeoutError:
        logger.warning(f"Scan {scan.id} timed out after {timeout}s")
        scan.status = "timeout"
        scan.finished_at = datetime.now(timezone.utc)
        scan.outputs = f"Scan timed out after {timeout}s"
        session.add(scan)
        session.commit()
        raise HTTPException(
            status_code=504,
            detail=f"Scan timed out after {timeout}s. Check tool availability and network connectivity.",
        )

    except Exception as exc:
        logger.error(f"Scan {scan.id} failed: {exc}", exc_info=True)
        scan.status = "failed"
        scan.finished_at = datetime.now(timezone.utc)
        scan.outputs = str(exc)[:500]
        session.add(scan)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(exc)[:200]}")

    return {
        "scan_id": scan.id,
        "target": target_name,
        "mode": mode,
        "endpoint_count": endpoint_count,
        "status": "completed",
        "outputs": outputs,
    }


