import type { InteractiveDiagramBlueprint } from '../types';

export const branchingDemo: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Chest Pain Diagnostic Pathway',
  narrativeIntro: 'A 55-year-old patient presents to the emergency department with chest pain. As the attending physician, you must make diagnostic and treatment decisions. Each choice affects the patient outcome.',
  diagram: {
    assetPrompt: 'Medical decision tree diagram showing a branching scenario for chest pain diagnosis, clean clinical illustration',
    zones: [],
  },
  labels: [],
  tasks: [
    { id: 't-1', type: 'label_diagram', questionText: 'Navigate the diagnostic pathway by making clinical decisions', requiredToProceed: true },
  ],
  animationCues: {
    correctPlacement: 'pulse',
    incorrectPlacement: 'shake',
    allLabeled: 'confetti',
  },
  mechanics: [
    { type: 'branching_scenario', scoring: { strategy: 'per_zone', points_per_correct: 20, max_score: 100 }, feedback: { on_correct: 'Good clinical judgment!', on_incorrect: 'Consider the clinical evidence more carefully.', on_completion: 'Case complete! Review your diagnostic pathway.' } },
  ],
  interactionMode: 'branching_scenario',
  branchingConfig: {
    nodes: [
      {
        id: 'node-start',
        question: 'The patient reports sudden-onset crushing chest pain radiating to the left arm, with diaphoresis. What is your first priority?',
        narrative_text: 'A 55-year-old male arrives via ambulance complaining of severe chest pain that started 30 minutes ago.',
        node_type: 'decision',
        options: [
          { id: 'opt-ecg', text: 'Order a 12-lead ECG immediately', nextNodeId: 'node-ecg', isCorrect: true, quality: 'optimal', points: 20, consequence_text: 'ECG obtained within 5 minutes — excellent triage.' },
          { id: 'opt-history', text: 'Take a detailed medical history first', nextNodeId: 'node-history', isCorrect: false, quality: 'suboptimal', points: 5, consequence_text: 'While history is important, delaying ECG in suspected MI increases risk.' },
          { id: 'opt-xray', text: 'Order a chest X-ray', nextNodeId: 'node-xray', isCorrect: false, quality: 'suboptimal', points: 5, consequence_text: 'Chest X-ray is useful but not the first priority in acute chest pain with these symptoms.' },
        ],
      },
      {
        id: 'node-ecg',
        question: 'The ECG shows ST-elevation in leads II, III, and aVF. What does this indicate?',
        narrative_text: 'The 12-lead ECG results are back within 4 minutes.',
        node_type: 'decision',
        options: [
          { id: 'opt-stemi', text: 'ST-Elevation Myocardial Infarction (STEMI) — inferior wall', nextNodeId: 'node-treatment', isCorrect: true, quality: 'optimal', points: 20, consequence_text: 'Correct! ST elevation in II, III, aVF indicates an inferior STEMI.' },
          { id: 'opt-nstemi', text: 'Non-ST-Elevation MI (NSTEMI)', nextNodeId: 'node-wrong-dx', isCorrect: false, quality: 'suboptimal', points: 5, consequence_text: 'NSTEMI shows ST depression or T-wave changes, not ST elevation.' },
          { id: 'opt-pericarditis', text: 'Pericarditis', nextNodeId: 'node-wrong-dx', isCorrect: false, quality: 'acceptable', points: 10, consequence_text: 'Pericarditis usually shows diffuse ST elevation, not localized to specific leads.' },
        ],
      },
      {
        id: 'node-history',
        question: 'You\'ve taken the history. The patient is worsening. What now?',
        narrative_text: 'Five minutes have passed. The patient is becoming more diaphoretic.',
        node_type: 'decision',
        options: [
          { id: 'opt-ecg-late', text: 'Rush to get a 12-lead ECG now', nextNodeId: 'node-ecg', isCorrect: true, quality: 'acceptable', points: 10, consequence_text: 'ECG obtained, but later than ideal. Every minute counts in MI.' },
          { id: 'opt-wait', text: 'Continue taking history', nextNodeId: 'node-bad-end', isCorrect: false, quality: 'harmful', points: 0, consequence_text: 'Further delay in a suspected MI is dangerous.' },
        ],
      },
      {
        id: 'node-xray',
        question: 'The chest X-ray is unremarkable. The patient\'s pain is worsening. What next?',
        narrative_text: 'X-ray shows no pneumothorax or obvious abnormality.',
        node_type: 'decision',
        options: [
          { id: 'opt-ecg-late2', text: 'Get a 12-lead ECG immediately', nextNodeId: 'node-ecg', isCorrect: true, quality: 'acceptable', points: 10, consequence_text: 'Good call, but time was lost. ECG should have been first.' },
          { id: 'opt-ct', text: 'Order a CT scan', nextNodeId: 'node-bad-end', isCorrect: false, quality: 'suboptimal', points: 0, consequence_text: 'CT is not first-line for suspected MI. Precious time is being wasted.' },
        ],
      },
      {
        id: 'node-treatment',
        question: 'Confirmed inferior STEMI. What is the best treatment approach?',
        narrative_text: 'The cardiologist has been notified. You need to initiate treatment.',
        node_type: 'decision',
        options: [
          { id: 'opt-pci', text: 'Activate the cath lab for primary PCI (percutaneous coronary intervention)', nextNodeId: 'node-good-end', isCorrect: true, quality: 'optimal', points: 20, consequence_text: 'Primary PCI within 90 minutes is the gold standard for STEMI treatment.' },
          { id: 'opt-thrombo', text: 'Administer thrombolytics', nextNodeId: 'node-ok-end', isCorrect: true, quality: 'acceptable', points: 15, consequence_text: 'Thrombolytics are acceptable if PCI is not available within 120 minutes.' },
          { id: 'opt-observe', text: 'Admit for observation and serial troponins', nextNodeId: 'node-bad-end', isCorrect: false, quality: 'harmful', points: 0, consequence_text: 'STEMI requires immediate intervention, not observation.' },
        ],
      },
      {
        id: 'node-wrong-dx',
        question: 'The cardiologist disagrees with your diagnosis. Review: ST elevation in II, III, aVF is most consistent with...',
        narrative_text: 'The consulting cardiologist reviews the ECG.',
        node_type: 'decision',
        options: [
          { id: 'opt-correct', text: 'Inferior STEMI — activate cath lab', nextNodeId: 'node-good-end', isCorrect: true, quality: 'acceptable', points: 15, consequence_text: 'Correct on second assessment. The delay was minor.' },
          { id: 'opt-still-wrong', text: 'Continue with original assessment', nextNodeId: 'node-bad-end', isCorrect: false, quality: 'harmful', points: 0, consequence_text: 'Ignoring specialist input led to a poor outcome.' },
        ],
      },
      {
        id: 'node-good-end',
        question: '',
        node_type: 'ending',
        isEndNode: true,
        endMessage: 'Excellent clinical pathway! The patient received timely PCI and had a good recovery. Your quick recognition of STEMI and appropriate treatment saved the patient.',
        ending_type: 'good',
        options: [],
      },
      {
        id: 'node-ok-end',
        question: '',
        node_type: 'ending',
        isEndNode: true,
        endMessage: 'The patient received thrombolytics and stabilized. While PCI would have been ideal, thrombolysis was an acceptable alternative given the circumstances.',
        ending_type: 'neutral',
        options: [],
      },
      {
        id: 'node-bad-end',
        question: '',
        node_type: 'ending',
        isEndNode: true,
        endMessage: 'Unfortunately, the delays in diagnosis and treatment led to a larger infarction. In acute chest pain with classic MI symptoms, rapid ECG and intervention are critical.',
        ending_type: 'bad',
        options: [],
      },
    ],
    startNodeId: 'node-start',
    showPathTaken: true,
    allowBacktrack: true,
    showConsequences: true,
    multipleValidEndings: true,
    instructions: 'Read each clinical scenario and choose the best course of action. Your decisions affect patient outcome.',
    narrative_structure: 'branching',
  },
  feedbackMessages: {
    perfect: 'Outstanding clinical judgment! You followed evidence-based guidelines throughout.',
    good: 'Good overall approach, but some decisions could have been more timely.',
    retry: 'Remember: in suspected MI, time is muscle. ECG first, then treat based on findings.',
  },
};
