import { useState, useCallback } from 'react';
import ChatWindow from './components/ChatWindow';
import AssessmentWizard from './components/AssessmentWizard';
import TrendDashboard from './components/TrendDashboard';
import TabBar from './components/TabBar';
import useUserProfile from './hooks/useUserProfile';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const { userId, profile, isReturningUser, isLoading } = useUserProfile();

  // Shared assessment result — bridges Assessment tab → Chat tab
  const [lastAssessment, setLastAssessment] = useState(null);

  const handleResultReady = useCallback((condition, result, answers) => {
    setLastAssessment({ condition, result, lifestyle_answers: answers, completedAt: Date.now() });
  }, []);

  const switchToChat = useCallback(() => setActiveTab('chat'), []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        {activeTab === 'chat' ? (
          <ChatWindow
            userId={isLoading ? null : userId}
            isReturningUser={isReturningUser}
            assessmentContext={lastAssessment}
            onClearAssessmentContext={() => setLastAssessment(null)}
          />
        ) : activeTab === 'progress' ? (
          <TrendDashboard userId={isLoading ? null : userId} />
        ) : (
          <AssessmentWizard
            userId={isLoading ? null : userId}
            profile={profile}
            isReturningUser={isReturningUser}
            onSwitchToChat={switchToChat}
            onResultReady={handleResultReady}
          />
        )}
      </div>
    </div>
  );
}

export default App;
