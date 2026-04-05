import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import AssessmentWizard from './components/AssessmentWizard';
import TabBar from './components/TabBar';
import useUserProfile from './hooks/useUserProfile';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const { userId, profile, isReturningUser, isLoading } = useUserProfile();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'chat' ? (
          <ChatWindow
            userId={isLoading ? null : userId}
            isReturningUser={isReturningUser}
          />
        ) : (
          <AssessmentWizard
            userId={isLoading ? null : userId}
            profile={profile}
            isReturningUser={isReturningUser}
            onSwitchToChat={() => setActiveTab('chat')}
          />
        )}
      </div>
    </div>
  );
}

export default App;
