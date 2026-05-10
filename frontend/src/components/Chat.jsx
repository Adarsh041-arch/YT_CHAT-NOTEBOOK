import { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { MessageCircle, Send, Loader2, Sparkles, Brain, AlertCircle } from 'lucide-react';

export default function Chat({ currentVideo, chatHistory, setChatHistory, sessionId, setSessionId }) {
  const { token } = useAuth();
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [error, setError] = useState(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, currentResponse, streaming]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;

    const question = input.trim();
    setInput('');
    setStreaming(true);
    setCurrentResponse('');
    setError(null);

    setChatHistory(prev => [...prev, { role: 'user', content: question }]);

    let fullResponse = '';
    let newSessionId = sessionId;

    try {
      await api.streamChat(currentVideo, question, sessionId, token, (chunk, receivedSessionId) => {
        if (receivedSessionId) newSessionId = receivedSessionId;
        fullResponse += chunk;
        setCurrentResponse(fullResponse);
      });

      if (newSessionId !== sessionId) {
        setSessionId(newSessionId);
      }

      setChatHistory(prev => [...prev, { role: 'assistant', content: fullResponse }]);
    } catch (err) {
      setError(err.message);
      setChatHistory(prev => [...prev, { role: 'assistant', content: err.message }]);
    } finally {
      setStreaming(false);
      setCurrentResponse('');
    }
  };

  return (
    <main className="flex-1 flex flex-col h-screen bg-dark-900">
      <header className="px-8 py-6 border-b border-dark-700">
        <h2 className="text-xl font-semibold text-white flex items-center gap-3">
          <MessageCircle className="w-6 h-6 text-primary" />
          Conversation
        </h2>
      </header>

      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {chatHistory.length === 0 && !currentVideo && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 bg-dark-800 rounded-3xl flex items-center justify-center mb-6">
              <MessageCircle className="w-10 h-10 text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Start a conversation</h3>
            <p className="text-slate-400 max-w-md">
              Load a YouTube video from the sidebar and ask questions about its content. 
              The AI will analyze the transcript and provide accurate answers.
            </p>
          </div>
        )}

        {chatHistory.length === 0 && currentVideo && !streaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-3xl flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Ready to chat</h3>
            <p className="text-slate-400 max-w-md">
              Ask any question about the video. The AI has analyzed the transcript and is ready to help.
            </p>
          </div>
        )}

        {chatHistory.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
          >
            <div
              className={`max-w-[70%] rounded-2xl px-5 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-primary to-secondary text-white rounded-br-md'
                  : 'bg-dark-800 text-slate-100 border border-dark-700 rounded-bl-md'
              }`}
            >
              <p className="text-xs font-medium opacity-60 mb-1 uppercase tracking-wider">
                {msg.role === 'user' ? 'You' : 'AI Assistant'}
              </p>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}

        {streaming && currentResponse === '' && (
          <div className="flex justify-start animate-fadeIn">
            <div className="max-w-[70%] rounded-2xl px-5 py-3 bg-dark-800 text-slate-100 border border-dark-700 rounded-bl-md">
              <p className="text-xs font-medium opacity-60 mb-1 uppercase tracking-wider">AI Assistant</p>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Thinking</span>
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </span>
              </div>
            </div>
          </div>
        )}

        {currentResponse && (
          <div className="flex justify-start animate-fadeIn">
            <div className="max-w-[70%] rounded-2xl px-5 py-3 bg-dark-800 text-slate-100 border border-dark-700 rounded-bl-md">
              <p className="text-xs font-medium opacity-60 mb-1 uppercase tracking-wider">AI Assistant</p>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{currentResponse}</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mx-8 mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-sm text-red-400 font-medium">Connection Error</p>
              <p className="text-xs text-red-300/80 mt-1">{error}</p>
            </div>
          </div>
        )}
      </div>

      <div className="p-6 border-t border-dark-700">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={currentVideo ? "Ask a question about the video..." : "Load a video first..."}
              disabled={!currentVideo || streaming}
              className="w-full px-6 py-4 bg-dark-800 border border-dark-600 rounded-2xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || !currentVideo || streaming}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-gradient-to-r from-primary to-secondary text-white rounded-xl hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {streaming ? (
                <Loader2 className="animate-spin h-5 w-5" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
