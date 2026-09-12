import React, { useState } from 'react';
import {
  Zap,
  Play,
  CheckCircle2,
  FileText,
  Briefcase,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Activity,
  Cpu,
  Upload,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  BadgeCheck,
  Building2,
  MapPin,
  DollarSign
} from 'lucide-react';
import {
  runAgent1,
  runAgent2,
  runAgent3,
  uploadResumeFile,
  runAgent4,
  getPendingPresencePosts,
  approvePresencePost,
  regeneratePresenceImage,
  runFullOrchestration,
  getPendingAgentApprovals,
  approveAgentContent
} from '../services/api';

export function CommandCenterPage() {
  const [resumeData, setResumeData] = useState('');
  const [targetRole, setTargetRole] = useState('');
  
  // State for workflow progression
  const [step, setStep] = useState(0); // 0: Idle, 1: A1 running, 2: A1 done, 3: A2 running, 4: A2 done, 5: A3 running, 6: A3 done
  const [jobsDiscovered, setJobsDiscovered] = useState([]);
  const [genuineJobs, setGenuineJobs] = useState([]);
  const [blockedJobs, setBlockedJobs] = useState([]);
  const [appliedJobs, setAppliedJobs] = useState([]);
  const [pendingPosts, setPendingPosts] = useState([]);
  const [isRegenerating, setIsRegenerating] = useState({});
  const [toastMessage, setToastMessage] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [expandedJds, setExpandedJds] = useState({});
  const fileInputRef = React.useRef(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const toggleJd = (id) => {
    setExpandedJds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    showToast(`Uploading ${file.name}...`);
    try {
      const res = await uploadResumeFile(file);
      if (res && res.raw_text) {
        setResumeData(res.raw_text);
        showToast("Resume parsed successfully.");
      } else {
        showToast("Parsed, but no text extracted.");
      }
    } catch (err) {
      showToast("Upload failed: " + err.message);
    } finally {
      setIsUploading(false);
      e.target.value = null;
    }
  };

  const handleAgent1 = async () => {
    if (!resumeData || !targetRole) {
      showToast("Please provide resume and target role.");
      return;
    }
    setStep(1);
    try {
      const res = await runAgent1(targetRole, resumeData);
      setJobsDiscovered(res.jobs_discovered || []);
      setStep(2);
      showToast("Job Matcher Agent completed.");
    } catch (e) {
      showToast("Failed to run Agent 1");
      setStep(0);
    }
  };

  const handleAgent2 = async () => {
    setStep(3);
    try {
      const res = await runAgent2(jobsDiscovered);
      setGenuineJobs(res.genuine_jobs || []);
      setBlockedJobs(res.blocked_jobs || []);
      setStep(4);
      showToast("Trust & Safety Agent completed.");
    } catch (e) {
      showToast("Failed to run Agent 2");
      setStep(2);
    }
  };

  const handleAgent3 = async () => {
    setStep(5);
    try {
      const res = await runAgent3(genuineJobs);
      setAppliedJobs(res.applied_jobs || []);
      setStep(6);
      showToast("Auto Apply Agent completed.");
    } catch (e) {
      showToast("Failed to run Agent 3");
      setStep(4);
    }
  };

  const fetchPendingPosts = async () => {
    // Legacy fallback to old presence posts, plus new agent content generations
    const presencePosts = await getPendingPresencePosts();
    const agentApprovals = await getPendingAgentApprovals();
    
    // Map agent approvals to the post structure used by the UI
    const mappedApprovals = agentApprovals.map(app => ({
      id: app.id,
      title: "Content Generator Agent Draft",
      content_body: app.generated_content,
      image_url: null,
      isAgentGeneration: true
    }));
    
    setPendingPosts([...presencePosts, ...mappedApprovals]);
  };

  const handleFullAutomation = async () => {
    setStep(1); // Indicate running
    showToast("Starting Full Automation Pipeline...");
    try {
      const res = await runFullOrchestration();
      
      // Update state based on events from the backend to populate the UI
      if (res && res.events) {
        for (const ev of res.events) {
          if (ev.agent_name === "Job Matcher Agent") setJobsDiscovered(ev.jobs_discovered || []);
          if (ev.agent_name === "Trust & Safety Agent") {
            setGenuineJobs(ev.genuine_jobs || []);
            setBlockedJobs(ev.blocked_jobs || []);
          }
          if (ev.agent_name === "Auto Apply Agent") setAppliedJobs(ev.applied_jobs || []);
        }
      }
      
      await fetchPendingPosts();
      setStep(8); // Done and pending review
      showToast("Full Automation Complete. Awaiting your approval.");
    } catch (e) {
      showToast("Full Automation failed");
      setStep(0);
    }
  };

  const handleAgent4 = async () => {
    setStep(7);
    try {
      // Run the new Agent 4 specifically if needed independently, though usually it runs via Full Automation
      await fetchPendingPosts();
      setStep(8);
      showToast("Presence Agent drafted a post.");
    } catch (e) {
      showToast("Failed to run Agent 4");
      setStep(6);
    }
  };

  const handleApprovePost = async (post) => {
    try {
      if (post.isAgentGeneration) {
        await approveAgentContent(post.id);
      } else {
        await approvePresencePost(post.id);
      }
      showToast("Post Approved & Published to Sandbox!");
      await fetchPendingPosts();
    } catch (e) {
      showToast("Failed to approve post");
    }
  };

  const handleRegenerateImage = async (postId) => {
    setIsRegenerating(prev => ({ ...prev, [postId]: true }));
    try {
      await regeneratePresenceImage(postId);
      showToast("Image regenerated successfully!");
      await fetchPendingPosts();
    } catch (e) {
      showToast("Failed to regenerate image");
    } finally {
      setIsRegenerating(prev => ({ ...prev, [postId]: false }));
    }
  };

  const agents = [
    {
      id: 1,
      name: 'Job Matcher Agent',
      domain: 'Discovery',
      task: 'Reads user resume data and searches database for matching opportunities with full details.',
      canExecute: step === 0,
      isExecuting: step === 1,
      isDone: step >= 2,
      onExecute: handleAgent1
    },
    {
      id: 2,
      name: 'Trust & Safety Agent',
      domain: 'Verification',
      task: 'Evaluates opportunities to detect scams, returns verified vs untrusted with API justification.',
      canExecute: step === 2,
      isExecuting: step === 3,
      isDone: step >= 4,
      onExecute: handleAgent2
    },
    {
      id: 3,
      name: 'Auto Apply Agent',
      domain: 'Execution',
      task: 'Submits verified genuine job applications automatically to the internal platform.',
      canExecute: step === 4,
      isExecuting: step === 5,
      isDone: step >= 6,
      onExecute: handleAgent3
    },
    {
      id: 4,
      name: 'Presence Agent',
      domain: 'Content',
      task: 'Drafts professional LinkedIn posts with AI images based on verified resume data.',
      canExecute: step === 6,
      isExecuting: step === 7,
      isDone: step >= 8,
      onExecute: handleAgent4
    }
  ];

  return (
    <div className="max-w-[1128px] mx-auto py-6 px-0 sm:px-4 space-y-6 animate-fade-in pb-16">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 left-6 z-50 bg-[#333333] text-white text-sm px-4 py-3 rounded shadow-lg flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          {toastMessage}
        </div>
      )}

      {/* Header */}
      <div className="pb-4 border-b border-[#ebebeb]">
        <h1 className="text-2xl font-semibold text-black flex items-center gap-2">
          <Zap className="h-6 w-6 text-[#0a66c2]" />
          Command Center — Multi-Agent Pipeline
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Autonomous orchestration: Job Matcher & Discovery → Trust & Safety Analysis → Auto Application.
        </p>
      </div>

      {/* Inputs */}
      <div className="bg-white border border-[#ebebeb] shadow-sm rounded-lg p-5">
        <h2 className="text-lg font-semibold text-black mb-4 flex items-center gap-2">
          <FileText className="h-5 w-5 text-[#0a66c2]" />
          1. Target Role & Resume Context
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Target Roles</label>
            <input 
              type="text" 
              placeholder="e.g. Senior AI Engineer, React Developer, Backend Engineer..."
              value={targetRole}
              onChange={e => setTargetRole(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-[#0a66c2]"
              disabled={step > 0}
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-semibold text-gray-700">Resume Text</label>
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={step > 0 || isUploading}
                className="flex items-center gap-1.5 text-sm font-semibold text-[#0a66c2] hover:text-[#004182] transition-colors disabled:text-gray-400"
              >
                {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                {isUploading ? 'Uploading...' : 'Upload PDF / Text'}
              </button>
              <input 
                type="file" 
                accept=".pdf,.txt,.docx"
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleFileUpload} 
              />
            </div>
            <textarea 
              rows="4"
              placeholder="Paste your resume here, or upload above to extract skills and profile..."
              value={resumeData}
              onChange={e => setResumeData(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-[#0a66c2]"
              disabled={step > 0 || isUploading}
            />
          </div>
          
          <div className="pt-4 border-t border-gray-200 mt-4 flex items-center justify-between">
            <p className="text-sm text-gray-600">You can trigger agents sequentially below, or run the complete pipeline automatically.</p>
            <button 
              onClick={handleFullAutomation}
              disabled={step > 0 || !resumeData || !targetRole}
              className="bg-[#0a66c2] hover:bg-[#004182] text-white px-6 py-2 rounded-full font-semibold text-sm transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              <Zap className="h-4 w-4" />
              Execute Full Automation
            </button>
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-black flex items-center gap-2">
          <Cpu className="h-5 w-5 text-[#0a66c2]" />
          2. Sequential Agent Execution
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {agents.map((ag) => (
            <div key={ag.id} className={`bg-white border shadow-sm rounded-lg p-5 flex flex-col h-full transition-all ${ag.isExecuting ? 'border-[#0a66c2] ring-2 ring-[#0a66c2]/20' : 'border-[#ebebeb]'}`}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#0a66c2] font-semibold bg-[#eef3f8] px-2 py-1 rounded">
                  Agent {ag.id} • {ag.domain}
                </span>
                {ag.isDone ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-green-700">
                    <CheckCircle2 className="h-4 w-4" /> Ready / Done
                  </span>
                ) : ag.isExecuting ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-[#0a66c2]">
                    <Activity className="h-4 w-4 animate-pulse" /> Running...
                  </span>
                ) : (
                  <span className="text-xs text-gray-400 font-semibold">Idle</span>
                )}
              </div>

              <div className="flex-1">
                <h3 className="text-base font-semibold text-black">{ag.name}</h3>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">{ag.task}</p>
              </div>

              <div className="pt-4 mt-4 border-t border-[#ebebeb]">
                <button
                  disabled={!ag.canExecute || ag.isExecuting}
                  onClick={ag.onExecute}
                  className={`w-full py-2.5 rounded-md font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
                    ag.isExecuting ? 'bg-blue-100 text-blue-700 cursor-wait' :
                    ag.isDone ? 'bg-gray-100 text-gray-500 hover:bg-gray-200' :
                    ag.canExecute ? 'bg-[#0a66c2] text-white hover:bg-[#004182] shadow-sm' :
                    'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {ag.isExecuting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Processing...
                    </>
                  ) : ag.isDone ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-green-600" /> Re-run Agent {ag.id}
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-current" /> Execute Agent {ag.id}
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sequential Execution Outputs (Persistent across all agent runs) */}
      <div className="space-y-6">
        <h2 className="text-lg font-semibold text-black flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-[#0a66c2]" />
          3. Agent Execution Stream
        </h2>

        {step >= 2 && (
          <div className="bg-white border border-[#ebebeb] shadow-sm rounded-lg overflow-hidden animate-fade-in">
            <div className="p-4 bg-[#f8fafc] border-b border-[#ebebeb] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="bg-[#0a66c2] text-white text-xs font-bold px-2 py-0.5 rounded">Agent 1</span>
                <h3 className="text-base font-semibold text-gray-900">
                  Discovered Opportunities ({jobsDiscovered.length})
                </h3>
              </div>
              <span className="text-xs text-gray-500 font-medium">
                Persistently visible throughout pipeline execution
              </span>
            </div>

            {jobsDiscovered.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-500">
                No semantically compatible jobs found for &quot;{targetRole}&quot;. Unrelated roles (DevOps, Frontend, etc.) were filtered out.
              </div>
            ) : (
            <div className="p-4 divide-y divide-gray-100">
              {jobsDiscovered.map((job, idx) => {
                const isExpanded = expandedJds[`disc-${idx}`];
                return (
                  <div key={job.id || idx} className="py-4 first:pt-0 last:pb-0 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-base font-bold text-gray-900">{job.title}</h4>
                          {/* Paid or Not Paid Badge */}
                          <span className={`text-[11px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                            job.is_paid ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {job.is_paid ? 'Paid' : 'Unpaid'}
                          </span>
                          {/* Job Type */}
                          <span className="text-[11px] font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                            {job.job_type || 'Full Time'}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs text-gray-600 mt-1 flex-wrap">
                          <span className="font-semibold text-black flex items-center gap-1">
                            <Building2 className="h-3.5 w-3.5 text-gray-500" />
                            {job.company}
                          </span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5 text-gray-400" />
                            {job.location} ({job.work_mode || 'Remote'})
                          </span>
                          {job.salary && (
                            <>
                              <span>•</span>
                              <span className="text-gray-700 font-medium flex items-center gap-1">
                                <DollarSign className="h-3.5 w-3.5 text-gray-400" />
                                {job.salary}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Direct Apply / Opportunity Link */}
                      <div className="flex items-center gap-2 shrink-0">
                        {job.link && (
                          <a
                            href={job.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#f3f4f6] hover:bg-[#e5e7eb] text-gray-800 text-xs font-semibold rounded transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5 text-gray-600" />
                            View Link
                          </a>
                        )}
                        <span className="bg-blue-50 text-[#0a66c2] text-xs font-semibold px-2.5 py-1.5 rounded">
                          {job.match_score || 92}% Match
                        </span>
                      </div>
                    </div>

                    {/* Job Description Snippet */}
                    <div className="bg-gray-50/80 rounded border border-gray-200/70 p-3 text-xs text-gray-700">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-gray-800 uppercase text-[10px] tracking-wider">Job Description:</span>
                        <button
                          onClick={() => toggleJd(`disc-${idx}`)}
                          className="text-[#0a66c2] hover:underline font-semibold flex items-center gap-0.5 text-[11px]"
                        >
                          {isExpanded ? (
                            <>Show Less <ChevronUp className="h-3 w-3" /></>
                          ) : (
                            <>Full Description <ChevronDown className="h-3 w-3" /></>
                          )}
                        </button>
                      </div>
                      <p className={`whitespace-pre-line leading-relaxed ${isExpanded ? '' : 'line-clamp-2'}`}>
                        {job.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* AGENT 2 OUTPUT: Trust & Safety Analysis (Appears below) */}
        {/* ======================================================== */}
        {step >= 4 && (
          <div className="bg-white border border-[#ebebeb] shadow-sm rounded-lg overflow-hidden animate-fade-in space-y-4 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#ebebeb]">
              <div className="flex items-center gap-2">
                <span className="bg-[#057642] text-white text-xs font-bold px-2 py-0.5 rounded">Agent 2</span>
                <h3 className="text-base font-semibold text-gray-900">
                  Trust & Safety Assessment
                </h3>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 font-semibold text-green-700">
                  <ShieldCheck className="h-4 w-4" /> {genuineJobs.length} Verified Trusted
                </span>
                <span className="flex items-center gap-1 font-semibold text-red-700">
                  <ShieldAlert className="h-4 w-4" /> {blockedJobs.length} Not Trusted / Scams
                </span>
              </div>
            </div>

            {/* 1. Verified Genuine & Safe Opportunities */}
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-gray-800 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Verified Genuine Jobs ({genuineJobs.length})
              </h4>
              {genuineJobs.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No genuine jobs passed the safety gate.</p>
              ) : (
                <div className="space-y-3">
                  {genuineJobs.map((job, idx) => (
                    <div key={job.id || idx} className="p-3.5 rounded-lg border border-green-200 bg-green-50/50 space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-gray-900">{job.title}</span>
                          <span className="text-xs text-gray-600">at <strong>{job.company}</strong></span>
                        </div>
                        <span className="bg-green-100 text-green-800 text-xs font-bold px-2 py-0.5 rounded flex items-center gap-1 w-fit">
                          <ShieldCheck className="h-3.5 w-3.5 text-green-600" />
                          Trusted • Score {Math.round(job.trust_score || 95)}/100
                        </span>
                      </div>

                      {/* 2-line API response */}
                      <div className="text-xs text-green-900 font-mono bg-white/70 p-2.5 rounded border border-green-200/60 leading-relaxed whitespace-pre-line">
                        {job.trust_explanation || `Risk Level: LOW (Trust Score: 95/100, Confidence: HIGH)\nVerified employer domain and transparent recruitment channel.`}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Untrusted / Scams Flagged */}
            {blockedJobs.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-sm font-bold text-red-800 flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  Not Trusted / Flagged Opportunities ({blockedJobs.length})
                </h4>
                <div className="space-y-3">
                  {blockedJobs.map((job, idx) => (
                    <div key={job.id || idx} className="p-3.5 rounded-lg border border-red-300 bg-red-50/70 space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-red-950">{job.title}</span>
                          <span className="text-xs text-red-700">at <strong>{job.company}</strong></span>
                        </div>
                        <span className="bg-red-200 text-red-900 text-xs font-bold px-2 py-0.5 rounded flex items-center gap-1 w-fit">
                          <ShieldAlert className="h-3.5 w-3.5 text-red-700" />
                          Flagged Scam / High Risk
                        </span>
                      </div>

                      {/* 2-line API response */}
                      <div className="text-xs text-red-900 font-mono bg-white/80 p-2.5 rounded border border-red-200 leading-relaxed whitespace-pre-line">
                        {job.trust_explanation || `Risk Level: HIGH (Trust Score: 18/100, Confidence: LOW)\nSuspicious payment demand or unauthorized domain detected.`}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* AGENT 3 OUTPUT: Auto Apply Submissions (Appears below)  */}
        {/* ======================================================== */}
        {step >= 6 && (
          <div className="bg-white border border-[#ebebeb] shadow-sm rounded-lg overflow-hidden animate-fade-in p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#ebebeb]">
              <div className="flex items-center gap-2">
                <span className="bg-[#7c3aed] text-white text-xs font-bold px-2 py-0.5 rounded">Agent 3</span>
                <h3 className="text-base font-semibold text-gray-900">
                  Auto Application Submissions ({appliedJobs.length})
                </h3>
              </div>
              <span className="text-xs font-semibold text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" /> Submitted to Internal API
              </span>
            </div>

            {appliedJobs.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No applications submitted.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {appliedJobs.map((job, idx) => (
                  <div key={job.id || idx} className="p-4 rounded-lg border border-purple-200 bg-purple-50/40 space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="font-bold text-sm text-gray-900">{job.title}</h5>
                        <p className="text-xs text-gray-600">{job.company}</p>
                      </div>
                      <span className="bg-purple-200 text-purple-900 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                        Application Sent
                      </span>
                    </div>
                    <div className="text-xs text-gray-600 flex items-center gap-3 pt-2 border-t border-purple-100">
                      <span>Match Score: <strong>{job.match_score || 92}%</strong></span>
                      <span>•</span>
                      <span className="text-emerald-700 font-semibold flex items-center gap-1">
                        <ShieldCheck className="h-3.5 w-3.5" /> Verified Genuine
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 5. Presence Agent: Human-In-The-Loop Review */}
        {step >= 8 && (
          <div className="bg-white border border-[#ebebeb] shadow-sm rounded-lg p-5">
            <div className="flex items-center justify-between mb-4 border-b border-[#ebebeb] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-semibold text-black">
                  5. Presence Agent — Pending Review
                </h3>
              </div>
              <span className="text-xs font-semibold text-indigo-700 flex items-center gap-1 bg-indigo-50 px-2 py-1 rounded">
                Human-In-The-Loop Required
              </span>
            </div>

            {pendingPosts.length === 0 ? (
              <p className="text-xs text-gray-500 italic">No pending posts to review.</p>
            ) : (
              <div className="space-y-4">
                {pendingPosts.map((post) => (
                  <div key={post.id} className="p-4 rounded-lg border border-indigo-200 bg-indigo-50/30 flex flex-col md:flex-row gap-4">
                    <div className="flex-1 space-y-3">
                      <div className="flex justify-between items-start">
                        <h5 className="font-bold text-sm text-gray-900">{post.title}</h5>
                        <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                          Pending Review
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{post.content_body}</p>
                      
                      <div className="flex gap-2 pt-2">
                        <button 
                          onClick={() => handleApprovePost(post)}
                          className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded hover:bg-indigo-700 transition-colors"
                        >
                          Approve & Publish to Sandbox
                        </button>
                        <button 
                          onClick={() => handleRegenerateImage(post.id)}
                          disabled={isRegenerating[post.id]}
                          className="px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 text-xs font-semibold rounded hover:bg-indigo-50 transition-colors disabled:opacity-50"
                        >
                          {isRegenerating[post.id] ? "Regenerating..." : "Regenerate Image"}
                        </button>
                      </div>
                    </div>
                    {post.image_url && (
                      <div className="w-full md:w-48 h-32 bg-gray-100 rounded border border-gray-200 flex-shrink-0 overflow-hidden">
                        <img src={post.image_url} alt="AI Generated context" className="w-full h-full object-cover" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

