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
    'roadmap',
  ],
};

export default sidebars;
