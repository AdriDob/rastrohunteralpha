import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/layout/Layout';
import MissionControl from './pages/MissionControl';
import OpportunityRadar from './pages/OpportunityRadar';
import HotPaths from './pages/HotPaths';
import AttackSurface from './pages/AttackSurface';
import HypothesisQueue from './pages/HypothesisQueue';
import FindingsPipeline from './pages/FindingsPipeline';
import EvidenceCenter from './pages/EvidenceCenter';
import ReportCenter from './pages/ReportCenter';
import TargetDetail from './pages/TargetDetail';
import EndpointDetail from './pages/EndpointDetail';
import FindingDetail from './pages/FindingDetail';

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 30_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<MissionControl />} />
            <Route path="/radar" element={<OpportunityRadar />} />
            <Route path="/hot-paths" element={<HotPaths />} />
            <Route path="/surface" element={<AttackSurface />} />
            <Route path="/hypotheses" element={<HypothesisQueue />} />
            <Route path="/pipeline" element={<FindingsPipeline />} />
            <Route path="/evidence" element={<EvidenceCenter />} />
            <Route path="/reports" element={<ReportCenter />} />
            <Route path="/target/:id" element={<TargetDetail />} />
            <Route path="/endpoint/:id" element={<EndpointDetail />} />
            <Route path="/finding/:id" element={<FindingDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
