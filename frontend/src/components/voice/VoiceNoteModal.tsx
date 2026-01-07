import { useState, useEffect, useRef } from 'react';
import { Mic, X, Play, Square, Send } from 'lucide-react';

interface VoiceNoteSample {
  id: string;
  name: string;
  duration: string;
  transcription: string;
  description: string;
}

const voiceSamples: VoiceNoteSample[] = [
  {
    id: 'voice-1',
    name: 'Clear Order',
    duration: '0:12',
    transcription: "Hi, this is James from Saruni Mara. We need 50 kilos of rice, 20 liters of cooking oil, and 10 trays of eggs for delivery on Friday please.",
    description: 'Clear, well-articulated order',
  },
  {
    id: 'voice-2',
    name: 'Informal Order',
    duration: '0:18',
    transcription: "Hey yeah um... this is Mama Riziki from Governors Camp... we need like, you know, the usual stuff... some rice, maybe like 30 kilos or so, and uh... what else... oh yeah toilet paper, probably 20 rolls, and some bottled water... let's say 5 crates? Thanks!",
    description: 'Casual with filler words and vague quantities',
  },
  {
    id: 'voice-3',
    name: 'Swahili Order',
    duration: '0:15',
    transcription: "Habari! Mimi ni Peter kutoka Angama Mara Lodge. Tunahitaji mchele kilo hamsini, sukari kilo kumi, na maziwa lita ishirini. Tafadhali leta kesho asubuhi.",
    description: 'Full Swahili order',
  },
  {
    id: 'voice-4',
    name: 'Noisy Background',
    duration: '0:20',
    transcription: "Hello... [background noise]... this is... from Lake Nakuru Lodge... we need... twenty kilos of... [unclear]... and about... boxes of tissue... also some cooking... fifteen liters I think... for Tuesday delivery if possible...",
    description: 'Transcription with gaps from poor audio',
  },
  {
    id: 'voice-5',
    name: 'Reference to Previous',
    duration: '0:08',
    transcription: "Hey it's Grace from Saruni Mara again. Can we get the same order as last time? Just double the eggs though. Need it by tomorrow morning.",
    description: 'References previous order history',
  },
];

interface VoiceNoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSend: (transcription: string, messageType: string) => void;
}

type RecordingState = 'idle' | 'recording' | 'transcribing' | 'ready';

export function VoiceNoteModal({ isOpen, onClose, onSend }: VoiceNoteModalProps) {
  const [selectedSample, setSelectedSample] = useState<VoiceNoteSample | null>(null);
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [transcriptionText, setTranscriptionText] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptionRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedSample(null);
      setRecordingState('idle');
      setTranscriptionText('');
      setRecordingTime(0);
      if (timerRef.current) clearInterval(timerRef.current);
      if (transcriptionRef.current) clearTimeout(transcriptionRef.current);
    }
  }, [isOpen]);

  // Recording timer
  useEffect(() => {
    if (recordingState === 'recording') {
      timerRef.current = setInterval(() => {
        setRecordingTime((t) => t + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [recordingState]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSampleSelect = (sample: VoiceNoteSample) => {
    setSelectedSample(sample);
    setRecordingState('idle');
    setTranscriptionText('');
    setRecordingTime(0);
  };

  const handleStartRecording = () => {
    if (!selectedSample) return;
    setRecordingState('recording');
    setRecordingTime(0);
    setTranscriptionText('');
  };

  const handleStopRecording = () => {
    if (!selectedSample) return;
    setRecordingState('transcribing');

    // Simulate transcription with typewriter effect
    const text = selectedSample.transcription;
    let index = 0;
    const typeSpeed = 30; // ms per character

    const typeChar = () => {
      if (index < text.length) {
        setTranscriptionText(text.substring(0, index + 1));
        index++;
        transcriptionRef.current = setTimeout(typeChar, typeSpeed);
      } else {
        setRecordingState('ready');
      }
    };

    // Small delay before starting transcription
    setTimeout(typeChar, 500);
  };

  const handleSend = () => {
    if (selectedSample && recordingState === 'ready') {
      onSend(selectedSample.transcription, 'voice_transcription');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-white font-semibold">Voice Note Simulation</h2>
              <p className="text-green-100 text-sm">Select a sample and simulate recording</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex">
          {/* Sample Selection */}
          <div className="w-1/2 border-r p-4 max-h-96 overflow-y-auto">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Voice Samples</h3>
            <div className="space-y-2">
              {voiceSamples.map((sample) => (
                <button
                  key={sample.id}
                  onClick={() => handleSampleSelect(sample)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    selectedSample?.id === sample.id
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-gray-800">{sample.name}</span>
                    <span className="text-xs text-gray-400">{sample.duration}</span>
                  </div>
                  <p className="text-xs text-gray-500">{sample.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Recording Area */}
          <div className="w-1/2 p-6 flex flex-col">
            {!selectedSample ? (
              <div className="flex-1 flex items-center justify-center text-center">
                <div className="text-gray-400">
                  <Mic className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Select a voice sample to begin</p>
                </div>
              </div>
            ) : (
              <>
                {/* Waveform / Recording Status */}
                <div className="flex-1 flex flex-col items-center justify-center">
                  {recordingState === 'idle' && (
                    <div className="text-center">
                      <p className="text-sm text-gray-600 mb-4">Ready to simulate: {selectedSample.name}</p>
                      <button
                        onClick={handleStartRecording}
                        className="w-20 h-20 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white shadow-lg transition-all hover:scale-105"
                      >
                        <Play className="w-8 h-8 ml-1" />
                      </button>
                      <p className="text-xs text-gray-400 mt-3">Click to start recording</p>
                    </div>
                  )}

                  {recordingState === 'recording' && (
                    <div className="text-center">
                      {/* Animated Waveform */}
                      <div className="flex items-center justify-center gap-1 h-16 mb-4">
                        {[...Array(20)].map((_, i) => (
                          <div
                            key={i}
                            className="w-1 bg-green-500 rounded-full animate-pulse"
                            style={{
                              height: `${Math.random() * 100}%`,
                              animationDelay: `${i * 50}ms`,
                              animationDuration: `${300 + Math.random() * 200}ms`,
                            }}
                          />
                        ))}
                      </div>
                      <p className="text-2xl font-mono text-gray-700 mb-4">{formatTime(recordingTime)}</p>
                      <button
                        onClick={handleStopRecording}
                        className="w-16 h-16 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white shadow-lg transition-all animate-pulse"
                      >
                        <Square className="w-6 h-6" />
                      </button>
                      <p className="text-xs text-gray-400 mt-3">Recording... Click to stop</p>
                    </div>
                  )}

                  {(recordingState === 'transcribing' || recordingState === 'ready') && (
                    <div className="w-full">
                      <div className="flex items-center gap-2 mb-3">
                        <div className={`w-2 h-2 rounded-full ${recordingState === 'transcribing' ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`} />
                        <span className="text-sm font-medium text-gray-600">
                          {recordingState === 'transcribing' ? 'Transcribing...' : 'Transcription Complete'}
                        </span>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 min-h-32 max-h-48 overflow-y-auto">
                        <p className="text-sm text-gray-700 leading-relaxed">
                          {transcriptionText}
                          {recordingState === 'transcribing' && (
                            <span className="inline-block w-0.5 h-4 bg-green-500 ml-0.5 animate-blink" />
                          )}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Send Button */}
                {recordingState === 'ready' && (
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={handleSend}
                      className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2 transition-colors"
                    >
                      <Send className="w-4 h-4" />
                      Send Voice Note
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
