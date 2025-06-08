import { useState, useRef, useEffect } from 'react'
import './App.css'

interface CompletionResponse {
  suggestions: string[];
  latency_ms: number;
  server_processing_time_ms: number;
}

function App() {
  const [text, setText] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [systemPrompt, setSystemPrompt] = useState('You are an autocomplete assistant. Your task is to suggest ONLY the next few words that would naturally complete the user\'s text. Do not add any additional context, explanations, or new sentences. Return only the continuation of the existing text. Keep suggestions concise and focused on completing the current thought.')
  const [latency, setLatency] = useState<{ total: number; server: number } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [selectedSuggestion, setSelectedSuggestion] = useState<number | null>(null)
  const [networkPingMs, setNetworkPingMs] = useState<number | null>(null)

  const fetchSuggestions = async (input: string) => {
    if (!input.trim()) {
      setSuggestions([])
      return
    }

    setLoading(true)
    setError(null)
    const requestStartTime = performance.now()

    try {
      const response = await fetch('http://localhost:8000/api/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: input,
          system_prompt: systemPrompt,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: CompletionResponse = await response.json()
      const requestEndTime = performance.now()
      
      setSuggestions(data.suggestions)
      setLatency({
        total: requestEndTime - requestStartTime,
        server: data.server_processing_time_ms
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch suggestions')
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchSuggestions(text)
    }, 100) // Reduced debounce time for better responsiveness

    return () => clearTimeout(timeoutId)
  }, [text, systemPrompt])

  // Ping latency endpoint on mount
  useEffect(() => {
    const ping = async () => {
      const start = performance.now()
      try {
        await fetch('http://localhost:8000/api/latency')
        const end = performance.now()
        setNetworkPingMs(end - start)
      } catch (e) {
        setNetworkPingMs(null)
      }
    }
    ping()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab' && suggestions.length > 0) {
      e.preventDefault()
      const suggestion = suggestions[selectedSuggestion ?? 0]
      if (suggestion) {
        const newText = text + suggestion
        setText(newText)
        setSuggestions([])
        setSelectedSuggestion(null)
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedSuggestion(prev => 
        prev === null ? 0 : (prev + 1) % suggestions.length
      )
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedSuggestion(prev => 
        prev === null ? suggestions.length - 1 : (prev - 1 + suggestions.length) % suggestions.length
      )
    }
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
  }

  const handleSystemPromptChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSystemPrompt(e.target.value)
  }

  return (
    <div className="container">
      <h1>AI Autocomplete Demo</h1>
      
      {latency && (
        <div className="latency-info">
          <div>Network Latency: {(latency.total - latency.server).toFixed(2)}ms</div>
          <div>Server Processing: {latency.server.toFixed(2)}ms</div>
          <div>Total Latency: {latency.total.toFixed(2)}ms</div>
        </div>
      )}

      {networkPingMs !== null && (
        <div className="latency-info">
          <div>Initial Network Ping: {networkPingMs.toFixed(2)}ms</div>
        </div>
      )}

      <div className="system-prompt-container">
        <label htmlFor="system-prompt">System Prompt:</label>
        <input
          id="system-prompt"
          type="text"
          value={systemPrompt}
          onChange={handleSystemPromptChange}
          placeholder="Enter system prompt..."
        />
      </div>

      <div className="editor-container">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Start typing..."
          rows={10}
        />
        
        {suggestions.length > 0 && (
          <div className="suggestions-container">
            {suggestions.map((suggestion, index) => (
              <div
                key={index}
                className={`suggestion ${index === selectedSuggestion ? 'selected' : ''}`}
                onClick={() => {
                  setText(text + suggestion)
                  setSuggestions([])
                  setSelectedSuggestion(null)
                }}
              >
                {suggestion}
              </div>
            ))}
          </div>
        )}
      </div>

      {loading && <div className="loading">Loading suggestions...</div>}
      {error && <div className="error">{error}</div>}

      <div className="instructions">
        <h3>Instructions:</h3>
        <ul>
          <li>Type to see AI-powered suggestions</li>
          <li>Press TAB to accept the selected suggestion</li>
          <li>Use ↑/↓ arrows to navigate suggestions</li>
          <li>Click on a suggestion to accept it</li>
        </ul>
      </div>
    </div>
  )
}

export default App
