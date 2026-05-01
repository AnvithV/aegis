import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'what-is-aegis',
    {
      type: 'category',
      label: 'Using Aegis',
      items: [
        'using-aegis/submitting-a-query',
        'using-aegis/monitoring-a-job',
        'using-aegis/reading-results',
      ],
    },
    {
      type: 'category',
      label: 'How It Works',
      items: [
        'how-it-works/data-pipeline',
        'how-it-works/identity-resolution',
        'how-it-works/integrity-gate',
        'how-it-works/scoring',
        'how-it-works/feedback-loop',
      ],
    },
    {
      type: 'category',
      label: 'System Architecture',
      items: [
        'architecture/overview',
        'architecture/diagrams',
      ],
    },
    'data-sources',
    {
      type: 'category',
      label: 'API Reference',
      collapsed: false,
      items: [
        'api/index',
        'api/queries',
        'api/jobs',
        'api/candidates',
        'api/shortlists',
        'api/hitl',
        'api/refit',
        'api/system',
      ],
    },
    'roadmap',
  ],
};

export default sidebars;
