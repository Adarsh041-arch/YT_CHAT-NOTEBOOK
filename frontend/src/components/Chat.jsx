import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Send, Loader2, Sparkles, Edit3, Check, X, Copy, CheckCheck, ListMusic, MessageCircle, AlertCircle, BarChart3, Network, Activity, Workflow, ChevronRight, Maximize2 } from 'lucide-react';
import VisualizationRenderer from './visualizations/VisualizationRenderer';

const TIMESTAMP_RE = /\[(\d{1,2}):(\d{2})\]/g;

function preprocessTimestamps(text) {
  if (typeof text !== 'string') return text || '';
  return text.replace(TIMESTAMP_RE, (match, m, s) => {
    const seconds = parseInt(m) * 60 + parseInt(s);
    return `<a class="timestamp-link" data-seek="${seconds}">${match}</a>`;
  });
}

function SessionRenamer({ sessionId, sessionName, setSessionName, token }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(sessionName);

  useEffect(() => { setDraft(sessionName); }, [sessionName]);

  const handleSave = async () => {
    if (!sessionId || !draft.trim()) return;
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ title: draft.trim() }),
      });
      setSessionName(draft.trim());
      setEditing(false);
    } catch { setEditing(false); }
  };

  const handleCancel = () => { setDraft(sessionName); setEditing(false); };

  if (!sessionId) return null;

  return editing ? (
    <div className="flex items-center gap-1">
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') handleCancel(); }}
        className="w-32 px-2 py-1 text-xs bg-dark-700 border border-dark-600 rounded text-white focus:outline-none focus:ring-1 focus:ring-primary"
        autoFocus
      />
      <button onClick={handleSave} className="p-1 hover:text-emerald-400 transition-colors"><Check className="w-3.5 h-3.5" /></button>
      <button onClick={handleCancel} className="p-1 hover:text-red-400 transition-colors"><X className="w-3.5 h-3.5" /></button>
    </div>
  ) : (
    <button onClick={() => setEditing(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-dark-700 rounded-lg transition-all">
      <Edit3 className="w-3.5 h-3.5" />
      Rename
    </button>
  );
}

function CodeBlock({ children }) {
  const text = String(children || '').replace(/\n$/, '');
  const [codeCopied, setCodeCopied] = useState(false);
  return (
    <div className="relative group">
      <button
        onClick={() => { navigator.clipboard.writeText(text); setCodeCopied(true); setTimeout(() => setCodeCopied(false), 2000); }}
        className="absolute top-2 right-2 p-1.5 bg-dark-600/80 hover:bg-dark-500 rounded-lg opacity-0 group-hover:opacity-100 transition-all text-slate-400 hover:text-white"
      >
        {codeCopied ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
      <pre className="bg-dark-700 p-4 rounded-xl overflow-x-auto">{children}</pre>
    </div>
  );
}

export default function Chat({ currentVideo, currentVideoTitle, chatHistory, setChatHistory, sessionId, setSessionId, sessionName, setSessionName, playlistInfo, playerRef, onVizOpenChange, vizWidth = 500, setVizWidth }) {
  const { token } = useAuth();
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [error, setError] = useState(null);
  const chatEndRef = useRef(null);
  const [generatingVizIdx, setGeneratingVizIdx] = useState(null);
  const [activeViz, setActiveViz] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const resizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const handleResizeStart = (e) => {
    e.preventDefault();
    resizingRef.current = true;
    startXRef.current = e.clientX;
    startWidthRef.current = vizWidth;
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!resizingRef.current) return;
      const delta = startXRef.current - e.clientX; // Drag left to expand
      const newWidth = Math.max(380, Math.min(850, startWidthRef.current + delta));
      setVizWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (resizingRef.current) {
        resizingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [vizWidth, setVizWidth]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, currentResponse, streaming]);

  useEffect(() => {
    setActiveViz(null);
    setIsExpanded(false);
  }, [sessionId, currentVideo]);

  useEffect(() => {
    if (activeViz) {
      onVizOpenChange?.(true);
    }
  }, [activeViz, onVizOpenChange]);

  const [copiedId, setCopiedId] = useState(null);

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {}
  };

  const handleTimestampClick = (e) => {
    const link = e.target.closest('.timestamp-link');
    if (link && link.dataset.seek && playerRef?.current) {
      playerRef.current.seekTo(parseInt(link.dataset.seek));
    }
  };

  const MarkdownContent = ({ content }) => (
    <div
      onClick={handleTimestampClick}
      className="text-sm leading-relaxed [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-dark-600 [&_th]:bg-dark-700 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-semibold [&_th]:text-slate-200 [&_td]:border [&_td]:border-dark-600 [&_td]:px-3 [&_td]:py-2 [&_tr:not(:last-child)_td]:border-b-dark-600 [&_hr]:border-dark-600 [&_hr]:my-4 [&_blockquote]:border-l-4 [&_blockquote]:border-primary [&_blockquote]:pl-4 [&_blockquote]:text-slate-400 [&_code]:bg-dark-700 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm [&_pre]:bg-dark-700 [&_pre]:p-4 [&_pre]:rounded-xl [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_h1]:text-lg [&_h1]:font-bold [&_h1]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 [&_a]:text-primary [&_a]:hover:underline [&_strong]:text-slate-100 [&_.timestamp-link]:text-primary [&_.timestamp-link]:cursor-pointer [&_.timestamp-link]:hover:underline [&_.timestamp-link]:font-medium"
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          pre: CodeBlock,
        }}
      >
        {preprocessTimestamps(content)}
      </ReactMarkdown>
    </div>
  );

  const handleGenerateVisualization = async (msgIdx) => {
    setGeneratingVizIdx(msgIdx);
    try {
      let question = '';
      for (let i = msgIdx - 1; i >= 0; i--) {
        if (chatHistory[i].role === 'user') {
          question = chatHistory[i].content;
          break;
        }
      }
      const spec = await api.generateVisualization(
        currentVideo,
        question,
        chatHistory[msgIdx].content,
        token
      );
      if (spec && spec.type !== 'none') {
        setChatHistory(prev => {
          const updated = [...prev];
          updated[msgIdx] = { ...updated[msgIdx], visualization: spec };
          return updated;
        });
      }
    } catch (err) {
      console.error('Failed to generate visualization:', err);
    } finally {
      setGeneratingVizIdx(null);
    }
  };

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
      await api.streamChat(currentVideo, question, sessionId, token,
        (chunk, receivedSessionId) => {
          if (receivedSessionId) newSessionId = receivedSessionId;
          fullResponse += chunk;
          setCurrentResponse(fullResponse);
        }
      );

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
    <div className="flex-1 flex h-full min-w-0 bg-dark-900 overflow-hidden relative">
      <main className="flex-1 flex flex-col h-full min-w-0 border-r border-dark-700">
        <div className="h-1 bg-gradient-to-r from-primary via-secondary to-purple-500" />

      <header className="px-6 py-4 border-b border-dark-700 flex items-center gap-4 min-h-[72px]">
        {currentVideo ? (
          <>
            <img
              src={`https://img.youtube.com/vi/${currentVideo}/hqdefault.jpg`}
              alt=""
              className="w-12 h-9 rounded-lg object-cover flex-shrink-0 ring-1 ring-white/10"
            />
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-semibold text-white truncate">
                {currentVideoTitle || 'Loading...'}
              </h2>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="text-xs text-slate-500 font-mono">{currentVideo}</span>
                {playlistInfo?.playlist_id && (
                  <span className="text-xs text-primary flex items-center gap-1">
                    <ListMusic className="w-3 h-3" />
                    {playlistInfo.playlist_id.slice(0, 18)}...
                  </span>
                )}
              </div>
            </div>
            <SessionRenamer sessionId={sessionId} sessionName={sessionName} setSessionName={setSessionName} token={token} />
          </>
        ) : (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-dark-800 rounded-xl flex items-center justify-center">
              <Send className="w-5 h-5 text-slate-500" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">YTChatBot</h2>
              <p className="text-xs text-slate-500">Load a video to start</p>
            </div>
          </div>
        )}
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
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn group`}
          >
            <div
              className={`relative max-w-[70%] rounded-2xl px-5 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-primary to-secondary text-white rounded-br-md'
                  : 'bg-dark-800 text-slate-100 border border-dark-700 rounded-bl-md'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-medium opacity-60 uppercase tracking-wider">
                  {msg.role === 'user' ? 'You' : 'AI Assistant'}
                </p>
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => copyToClipboard(msg.content, `msg-${idx}`)}
                    className="p-1 rounded-lg opacity-0 group-hover:opacity-100 transition-all text-slate-500 hover:text-white hover:bg-dark-700 -mr-1 -mt-1"
                  >
                    {copiedId === `msg-${idx}` ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
              <MarkdownContent content={msg.content} />
              {msg.role === 'assistant' && !msg.visualization && (
                <button
                  onClick={() => handleGenerateVisualization(idx)}
                  disabled={generatingVizIdx === idx}
                  className="mt-3 w-full py-2 px-3 bg-dark-700/60 hover:bg-dark-700/90 border border-dark-600/60 hover:border-primary/40 rounded-xl transition-all flex items-center justify-center gap-2 text-xs text-slate-400 hover:text-white disabled:opacity-50"
                >
                  {generatingVizIdx === idx ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
                  ) : (
                    <><Sparkles className="w-3.5 h-3.5" /> Create Visualization</>
                  )}
                </button>
              )}
              {msg.visualization && (
                <div 
                  onClick={() => setActiveViz(msg.visualization)}
                  className="mt-3 p-3 bg-dark-700/60 hover:bg-dark-700/90 border border-dark-600/60 hover:border-primary/40 rounded-xl cursor-pointer transition-all flex items-center justify-between gap-3 group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors flex-shrink-0">
                      {msg.visualization.type === 'chart' && <BarChart3 className="w-4 h-4" />}
                      {msg.visualization.type === 'graph' && <Network className="w-4 h-4" />}
                      {(msg.visualization.type === 'simulation' || msg.visualization.type === 'custom') && <Activity className="w-4 h-4" />}
                      {msg.visualization.type === 'diagram' && <Workflow className="w-4 h-4" />}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-white truncate">
                        {msg.visualization.title || 'Interactive Visualization'}
                      </p>
                      <p className="text-[10px] text-slate-400 capitalize">Click to open {msg.visualization.type}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
                </div>
              )}
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
            <div className="max-w-[70%] rounded-2xl px-5 py-3 bg-dark-800 text-slate-100 border border-dark-700 rounded-bl-md streaming-text">
              <p className="text-xs font-medium opacity-60 mb-1 uppercase tracking-wider">AI Assistant</p>
              <MarkdownContent content={currentResponse} />
              <span className="inline-block w-2 h-4 bg-primary/70 rounded-sm ml-0.5 animate-pulse" />
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
      
      {/* Visualization Panel */}
      {activeViz && (
        <aside 
          style={{ width: vizWidth }}
          className="relative border-l border-dark-700 bg-dark-800 flex flex-col h-full overflow-hidden animate-slideIn flex-shrink-0"
        >
          {/* Resize handle */}
          <div
            onMouseDown={handleResizeStart}
            className="absolute top-0 left-0 w-1.5 h-full cursor-ew-resize hover:bg-primary/20 transition-colors z-50 group flex items-center justify-center"
            title="Drag to resize panel"
          >
            <div className="w-[2px] h-8 bg-dark-600 group-hover:bg-primary/80 rounded transition-colors" />
          </div>

          <div className="pl-2 flex-1 flex flex-col h-full overflow-hidden">
            <div className="px-6 py-4 border-b border-dark-700 flex items-center justify-between bg-dark-850">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 text-primary">
                  {activeViz.type === 'chart' && <BarChart3 className="w-4 h-4" />}
                  {activeViz.type === 'graph' && <Network className="w-4 h-4" />}
                  {(activeViz.type === 'simulation' || activeViz.type === 'custom') && <Activity className="w-4 h-4" />}
                  {activeViz.type === 'diagram' && <Workflow className="w-4 h-4" />}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-white truncate">
                    {activeViz.title || 'Visualization'}
                  </h3>
                  <p className="text-[10px] text-slate-500 capitalize">{activeViz.type} visualization</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setIsExpanded(true)}
                  title="Expand visualization"
                  className="p-1.5 hover:bg-dark-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setActiveViz(null)}
                  className="p-1.5 hover:bg-dark-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 flex flex-col min-h-0 bg-dark-900/10">
              <div className="w-full bg-dark-950/30 rounded-2xl border border-dark-700/50 p-6 flex flex-col items-stretch justify-center min-h-[350px]">
                <VisualizationRenderer spec={activeViz} />
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* Expanded Visualization Modal */}
      {isExpanded && activeViz && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-dark-950/80 backdrop-blur-md p-6 animate-fadeIn">
          <div className="bg-dark-900 border border-dark-700/80 rounded-3xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-dark-700 flex items-center justify-between bg-dark-850">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 text-primary">
                  {activeViz.type === 'chart' && <BarChart3 className="w-4 h-4" />}
                  {activeViz.type === 'graph' && <Network className="w-4 h-4" />}
                  {(activeViz.type === 'simulation' || activeViz.type === 'custom') && <Activity className="w-4 h-4" />}
                  {activeViz.type === 'diagram' && <Workflow className="w-4 h-4" />}
                </div>
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-white truncate">
                    {activeViz.title || 'Visualization'}
                  </h3>
                  <p className="text-xs text-slate-500 capitalize">{activeViz.type} visualization (Expanded)</p>
                </div>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="p-1.5 hover:bg-dark-700 rounded-lg transition-colors text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-auto p-8 flex flex-col items-center justify-center bg-dark-950/20 min-h-0">
              <div className="w-full h-full flex items-center justify-center min-h-0 min-w-0">
                <VisualizationRenderer spec={activeViz} isExpanded={true} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
