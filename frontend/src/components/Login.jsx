import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Play, Loader2, AlertCircle } from 'lucide-react';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(username, password);
      } else {
        await register(username, password);
        setIsLogin(true);
        setError('');
        alert('Account created! Please sign in.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-gradient-to-br from-primary/10 via-transparent to-secondary/10 pointer-events-none" />
      <div className="fixed top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl animate-pulse" />
      <div className="fixed bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />

      <div className="relative w-full max-w-md">
        <div className="text-center mb-8 animate-fadeIn">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary to-secondary rounded-2xl mb-4 shadow-lg shadow-primary/25">
            <Play className="w-8 h-8 text-white fill-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text">YTChatBot</h1>
          <p className="text-slate-400 mt-2">Chat with any YouTube video using AI</p>
        </div>

        <div className="glass rounded-2xl p-8 shadow-2xl animate-slideIn">
          <div className="flex bg-dark-700 rounded-xl p-1 mb-6">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isLogin 
                  ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-md' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                !isLogin 
                  ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-md' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                minLength={3}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={6}
                className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-primary to-secondary text-white font-semibold rounded-xl shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin h-5 w-5" />
                  Processing...
                </>
              ) : (
                isLogin ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          <p className="text-center text-slate-500 text-sm mt-6">
            {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="text-primary hover:text-secondary transition-colors"
            >
              {isLogin ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
