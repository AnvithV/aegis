import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/what-is-aegis">
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    title: 'Researcher Ranking',
    description:
      'Rank researchers based on multi-dimensional metrics drawn from publications, citations, grants, and collaborative impact.',
  },
  {
    title: 'Evidence-Backed',
    description:
      'Every score is traceable to specific data points. Transparent methodology ensures trust and reproducibility.',
  },
  {
    title: 'Continuously Learning',
    description:
      'The engine ingests fresh data on a regular cadence, keeping rankings current as the research landscape evolves.',
  },
];

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <section className={styles.features}>
          {features.map((feature, idx) => (
            <div key={idx} className={styles.featureCard}>
              <Heading as="h3">{feature.title}</Heading>
              <p>{feature.description}</p>
            </div>
          ))}
        </section>
      </main>
    </Layout>
  );
}
