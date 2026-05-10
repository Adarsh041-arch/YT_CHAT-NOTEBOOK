import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { api } from './services/api';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';

function AppContent() {
  const { token, loading } = useAuth();
  const [currentVideo, setCurrentVideo] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const handleLoadSession = async (session) => {
    if (!session) {
      setSessionId(null);
      setChatHistory([]);
      return;
    }

    try {
      const messages = await api.getSessionMessages(session.id, token);
      if (Array.isArray(messages)) {
        const history = [];
        let currentQ = '';
        for (const msg of messages) {
          if (msg.role === 'user') {
            currentQ = msg.content;
          } else {
            history.push({ role: 'user', content: currentQ });
            history.push({ role: 'assistant', content: msg.content });
          }
        }
        setChatHistory(history);
        setSessionId(session.id);
        setCurrentVideo(session.video_id);
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!token) {
    return <Login />;
  }

  return (
    <div className="flex h-screen bg-dark-900">
      <Sidebar
        currentVideo={currentVideo}
        setCurrentVideo={setCurrentVideo}
        onLoadSession={handleLoadSession}
        currentSessionId={sessionId}
        chatHistory={chatHistory}
        setChatHistory={setChatHistory}
      />
      <Chat
        currentVideo={currentVideo}
        chatHistory={chatHistory}
        setChatHistory={setChatHistory}
        sessionId={sessionId}
        setSessionId={setSessionId}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
