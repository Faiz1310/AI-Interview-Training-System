import React, { useState } from 'react';
import axios from 'axios';
import { Upload, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ResumeUploadPage({ onBack, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadedResumeId, setUploadedResumeId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [formData, setFormData] = useState({
    resume_file: null,
    job_role: '',
    jd_file: null,
    jd_text: '',
  });

  const handleFileChange = (e) => {
    const { name, files } = e.target;
    if (files && files[0]) {
      setFormData((prev) => ({ ...prev, [name]: files[0] }));
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      if (!formData.resume_file) {
        throw new Error('Please select a resume file');
      }
      if (!formData.job_role.trim()) {
        throw new Error('Please enter a job role');
      }
      if (!formData.jd_file && !formData.jd_text.trim()) {
        throw new Error('Please provide a job description (file or text)');
      }

      const form = new FormData();
      form.append('resume_file', formData.resume_file);
      form.append('job_role', formData.job_role);
      if (formData.jd_file) {
        form.append('jd_file', formData.jd_file);
      }
      if (formData.jd_text) {
        form.append('jd_text', formData.jd_text);
      }

      const token = localStorage.getItem('access_token');
      const response = await axios.post(`${API_URL}/upload_resume`, form, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      setSuccess(`✓ Resume uploaded successfully! ID: ${response.data.id}`);
      setUploadedResumeId(response.data.id);

      const analysisRes = await axios.post(
        `${API_URL}/analyze_resume`,
        { resume_id: response.data.id, force_refresh: false },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      setAnalysis(analysisRes.data);

      setFormData({ resume_file: null, job_role: '', jd_file: null, jd_text: '' });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReanalyze = async () => {
    const resumeId = analysis?.resume_id || uploadedResumeId;
    if (!resumeId) return;

    setReanalyzing(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const analysisRes = await axios.post(
        `${API_URL}/analyze_resume`,
        { resume_id: resumeId, force_refresh: true },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      setAnalysis(analysisRes.data);
      setSuccess('Resume analysis refreshed.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to re-analyze resume');
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
        >
          ← Back
        </button>
        <h2 className="text-3xl font-bold text-white">Upload Resume</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 bg-red-600/20 border border-red-600 text-red-300 rounded-lg flex items-start gap-3">
            <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {success && (
          <div className="p-4 bg-green-600/20 border border-green-600 text-green-300 rounded-lg flex items-start gap-3">
            <CheckCircle size={20} className="flex-shrink-0 mt-0.5" />
            <p>{success}</p>
          </div>
        )}

        {/* Resume Section */}
        <div className="bg-slate-800 p-6 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-white">Resume</h3>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Upload Resume (PDF, DOCX, or TXT)
            </label>
            <div className="relative">
              <input
                type="file"
                name="resume_file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                required
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            {formData.resume_file && (
              <p className="text-sm text-green-400 mt-2">✓ {formData.resume_file.name}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Job Role
            </label>
            <input
              type="text"
              name="job_role"
              value={formData.job_role}
              onChange={handleInputChange}
              placeholder="e.g., Senior Software Engineer"
              required
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Job Description Section */}
        <div className="bg-slate-800 p-6 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-white">Job Description</h3>
          
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Upload JD (PDF or DOCX)
            </label>
            <input
              type="file"
              name="jd_file"
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500"
            />
            {formData.jd_file && (
              <p className="text-sm text-green-400 mt-2">✓ {formData.jd_file.name}</p>
            )}
          </div>

          <div className="text-center text-slate-400">or</div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Paste Job Description Text
            </label>
            <textarea
              name="jd_text"
              value={formData.jd_text}
              onChange={handleInputChange}
              placeholder="Paste the job description here..."
              rows={6}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
        >
          <Upload size={20} />
          {loading ? 'Uploading...' : 'Upload & Analyze'}
        </button>

        {analysis && (
          <div className="bg-slate-800 p-6 rounded-lg space-y-4">
            <h3 className="text-lg font-semibold text-white">Resume Analysis</h3>
            {analysis.model_used === 'groq' && (
              <div className="p-3 bg-blue-600/20 border border-blue-500 rounded text-blue-200 text-sm">
                Primary AI unavailable. Showing fallback analysis.
              </div>
            )}
            {analysis.model_used === 'fallback' && (
              <div className="p-3 bg-yellow-600/20 border border-yellow-500 rounded text-yellow-200 text-sm">
                AI analysis unavailable. Showing basic evaluation.
              </div>
            )}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">Match Score</span>
                <span className="text-white font-semibold">{Math.round(analysis.score || 0)}%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full ${(analysis.score || 0) >= 60 ? 'bg-green-500' : 'bg-yellow-500'}`}
                  style={{ width: `${Math.max(0, Math.min(100, analysis.score || 0))}%` }}
                />
              </div>
            </div>

            {analysis.summary && <p className="text-slate-300 text-sm">{analysis.summary}</p>}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-green-400 font-medium mb-2">Strengths</h4>
                <ul className="list-disc list-inside text-slate-300 text-sm space-y-1">
                  {(analysis.strengths || []).map((s, i) => <li key={`st-${i}`}>{s}</li>)}
                </ul>
              </div>
              <div>
                <h4 className="text-yellow-400 font-medium mb-2">Weaknesses</h4>
                <ul className="list-disc list-inside text-slate-300 text-sm space-y-1">
                  {(analysis.weaknesses || []).map((w, i) => <li key={`wk-${i}`}>{w}</li>)}
                </ul>
              </div>
            </div>

            <div>
              <h4 className="text-blue-400 font-medium mb-2">Suggestions</h4>
              <ul className="list-disc list-inside text-slate-300 text-sm space-y-1">
                {(analysis.suggestions || []).map((s, i) => <li key={`sg-${i}`}>{s}</li>)}
              </ul>
            </div>

            {(analysis.resume_risk_flag || (analysis.score || 0) < (analysis.risk_threshold || 60)) && (
              <div className="p-3 bg-yellow-600/20 border border-yellow-500 rounded text-yellow-200 text-sm">
                Your resume is not strongly aligned with this role yet.
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleReanalyze}
                disabled={reanalyzing}
                className="px-4 py-2 bg-blue-700 hover:bg-blue-800 disabled:bg-blue-900 text-white rounded-lg transition inline-flex items-center gap-2"
              >
                <RefreshCw size={16} className={reanalyzing ? 'animate-spin' : ''} />
                {reanalyzing ? 'Re-analyzing...' : 'Re-analyze Resume'}
              </button>
              <button
                type="button"
                onClick={() => onSuccess?.(uploadedResumeId, 'interview')}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
              >
                Continue Interview
              </button>
              <button
                type="button"
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
              >
                Improve Resume First
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
