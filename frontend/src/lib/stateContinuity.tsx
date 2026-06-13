import { createContext, useContext, useState, type ReactNode, useCallback } from 'react';

interface FocusState {
  selectedActionId: string | null;
  assistantContext: string | null;
  decisionFocus: string | null;
}

interface StateContinuityContextValue {
  focus: FocusState;
  setSelectedAction: (id: string | null) => void;
  setAssistantContext: (ctx: string | null) => void;
  setDecisionFocus: (focus: string | null) => void;
  clearFocus: () => void;
}

const StateContinuityContext = createContext<StateContinuityContextValue | null>(null);

export function StateContinuityProvider({ children }: { children: ReactNode }) {
  const [focus, setFocus] = useState<FocusState>({
    selectedActionId: null,
    assistantContext: null,
    decisionFocus: null,
  });

  const setSelectedAction = useCallback((id: string | null) => {
    setFocus(prev => ({ ...prev, selectedActionId: id }));
  }, []);

  const setAssistantContext = useCallback((ctx: string | null) => {
    setFocus(prev => ({ ...prev, assistantContext: ctx }));
  }, []);

  const setDecisionFocus = useCallback((df: string | null) => {
    setFocus(prev => ({ ...prev, decisionFocus: df }));
  }, []);

  const clearFocus = useCallback(() => {
    setFocus({ selectedActionId: null, assistantContext: null, decisionFocus: null });
  }, []);

  return (
    <StateContinuityContext.Provider value={{
      focus, setSelectedAction, setAssistantContext, setDecisionFocus, clearFocus,
    }}>
      {children}
    </StateContinuityContext.Provider>
  );
}

export function useStateContinuity(): StateContinuityContextValue {
  const ctx = useContext(StateContinuityContext);
  if (!ctx) {
    throw new Error('useStateContinuity must be used within StateContinuityProvider');
  }
  return ctx;
}
