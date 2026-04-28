# Plan: Phase 4b — Docusaurus Documentation Site

> **Status:** COMPLETE (2026-04-27)
> All 10 tasks completed. Build succeeds. 8/8 acceptance criteria verified. Validated by agent team with build evidence.

## Build Evidence

> **Status:** COMPLETE
> **Date:** 2026-04-27
> **Team:** phase4b-docs-20260427-1500

### Validation Commands
- `test -f package.json && test -f docusaurus.config.ts && test -f sidebars.ts` — PASS ("Scaffold exists")
- `ls website/docs/*.mdx website/docs/**/*.mdx` — PASS (all 10 MDX files found)
- `test -f website/static/images/architecture.svg` — PASS ("Architecture image OK")
- `test -f .github/workflows/deploy-docs.yml` — PASS ("GH Actions OK")
- `grep "website/node_modules" .gitignore` — PASS ("Gitignore OK")
- `npm run build` — PASS (compiled successfully, static files generated in "build")

### Acceptance Criteria Verification
- [x] Docusaurus 3.x project at website/ with valid config — VERIFIED (@docusaurus/core ^3.7.0, docusaurus.config.ts and sidebars.ts present)
- [x] Custom homepage with hero and feature cards — VERIFIED (src/pages/index.tsx with hero section and feature cards)
- [x] 5-section sidebar — VERIFIED (what-is-aegis, How It Works [5 items], System Architecture [2 items], data-sources, roadmap)
- [x] 10 MDX content pages — VERIFIED (10 .mdx files across docs/, docs/how-it-works/, docs/architecture/)
- [x] Placeholder images — VERIFIED (architecture.svg 587B, data-flow.svg 584B in website/static/images/)
- [x] GitHub Actions workflow — VERIFIED (.github/workflows/deploy-docs.yml with push-to-main trigger and GitHub Pages deployment)
- [x] .gitignore updated — VERIFIED (website/node_modules/, website/.docusaurus/, website/build/ entries)
- [x] npm run build succeeds — VERIFIED (Client and Server compiled successfully, static files generated)

### Files Changed
| File | Action | Verified |
|------|--------|----------|
| website/package.json | Created | Yes |
| website/docusaurus.config.ts | Created | Yes |
| website/sidebars.ts | Created | Yes |
| website/src/pages/index.tsx | Created | Yes |
| website/src/css/custom.css | Created | Yes |
| website/docs/what-is-aegis.mdx | Created | Yes |
| website/docs/how-it-works/data-pipeline.mdx | Created | Yes |
| website/docs/how-it-works/identity-resolution.mdx | Created | Yes |
| website/docs/how-it-works/integrity-gate.mdx | Created | Yes |
| website/docs/how-it-works/scoring.mdx | Created | Yes |
| website/docs/how-it-works/feedback-loop.mdx | Created | Yes |
| website/docs/architecture/overview.mdx | Created | Yes |
| website/docs/architecture/diagrams.mdx | Created | Yes |
| website/docs/data-sources.mdx | Created | Yes |
| website/docs/roadmap.mdx | Created | Yes |
| website/static/images/architecture.svg | Created | Yes |
| website/static/images/data-flow.svg | Created | Yes |
| .github/workflows/deploy-docs.yml | Created | Yes |
| .gitignore | Modified | Yes |

> **EXECUTION DIRECTIVE**: This is a team-orchestrated plan.
> **FORBIDDEN**: Direct implementation (Edit, Write, NotebookEdit) by the main agent. If you are the main conversation agent and a user asks you to implement this plan, you MUST invoke `/build specs/aegis-phase4b-docs-site.md` -- do NOT implement it yourself.
> **REQUIRED**: Execute ONLY via the `/build` command, which deploys team agents to do the work.

## Task Description

Build a Docusaurus 3.x documentation website for Aegis, the internal researcher-ranking engine. The site lives at `website/` inside the existing aegis repo (github.com/AnvithV/aegis) and targets two audiences: engineers joining the team and internal stakeholders/leadership. The documentation is high-level only — no API reference, no module-level docs. The site has 5 sections: What is Aegis, How It Works, System Architecture, Data Sources, and Roadmap. Deployment is via GitHub Pages using a GitHub Actions workflow. All content pages use MDX format. Two placeholder images are included for architecture and data-flow diagrams.

## Objective

When this plan is complete:
1. A Docusaurus 3.x project exists at `website/` with a working local dev server (`npm start`) and production build (`npm run build`).
2. Five documentation sections with full MDX content covering What is Aegis, How It Works, System Architecture, Data Sources, and Roadmap.
3. Clean sidebar navigation matching the 5 sections with proper ordering.
4. Placeholder images at `website/static/images/architecture.png` and `website/static/images/data-flow.png`.
5. A GitHub Actions workflow at `.github/workflows/deploy-docs.yml` for GitHub Pages deployment.
6. No versioning, no API reference, no module-level docs — high-level documentation only.

## Problem Statement

Aegis has grown across 4 phases into a complex system with 3 researcher populations, ~25 data sources, a multi-component scoring engine, an integrity gate, a feedback loop, and a production API with a frontend. Engineers joining the team and internal stakeholders have no centralized, readable documentation to understand what Aegis does, how it works, and where it's headed. The existing `docs/` directory contains scattered design documents and phase plans written for agent execution, not human consumption. A proper documentation site is needed.

## Solution Approach

1. **Scaffold Docusaurus 3.x** at `website/` using the classic preset with a clean, minimal configuration. No versioning, no blog, no i18n — just docs.
2. **Write 5 sections of MDX content** organized into a docs directory structure that maps cleanly to sidebar navigation. Content is high-level, conceptual, and written for the two target audiences.
3. **Configure sidebar** to present the 5 sections in order with proper labels and collapsible categories.
4. **Add placeholder images** as simple SVG files (so they render immediately without external tooling) for architecture and data-flow diagrams.
5. **Create GitHub Actions workflow** that builds the Docusaurus site and deploys to GitHub Pages on pushes to `main` that touch `website/`.
6. **Validate** with `npm run build` producing a clean output with zero errors.

## Relevant Files

### Existing Files (read-only context)
- `docs/design/scoring.md` — Existing scoring design doc with architectural detail (reference for content accuracy)
- `docs/plans/aegis/README.md` — Phase plan index with phase descriptions and exit criteria (reference for Roadmap section)
- `docs/plans/aegis/phase-0-foundation.md` — Phase 0 plan (reference for Architecture section)
- `docs/plans/aegis/phase-1-scoring.md` — Phase 1 plan (reference for Architecture section)
- `docs/plans/aegis/phase-2-multi-population.md` — Phase 2 plan (reference for Architecture section)
- `docs/plans/aegis/phase-3-production.md` — Phase 3 plan (reference for Architecture section)
- `pyproject.toml` — Project metadata (name, description for homepage)
- `.gitignore` — May need update for `website/node_modules/`, `website/.docusaurus/`, `website/build/`

### New Files
- `website/package.json` — Docusaurus project dependencies
- `website/docusaurus.config.ts` — Docusaurus configuration (site title, URL, navbar, footer, preset)
- `website/sidebars.ts` — Sidebar configuration for the 5 documentation sections
- `website/tsconfig.json` — TypeScript config for Docusaurus
- `website/src/css/custom.css` — Custom CSS overrides (minimal)
- `website/src/pages/index.tsx` — Custom homepage (landing page with hero and feature cards)
- `website/docs/what-is-aegis.mdx` — Section 1: What is Aegis?
- `website/docs/how-it-works/data-pipeline.mdx` — Section 2a: Data pipeline
- `website/docs/how-it-works/identity-resolution.mdx` — Section 2b: Identity resolution
- `website/docs/how-it-works/integrity-gate.mdx` — Section 2c: Integrity gate
- `website/docs/how-it-works/scoring.mdx` — Section 2d: Scoring components
- `website/docs/how-it-works/feedback-loop.mdx` — Section 2e: Feedback loop
- `website/docs/architecture/overview.mdx` — Section 3a: Phase-by-phase overview
- `website/docs/architecture/diagrams.mdx` — Section 3b: Architecture and data-flow diagrams
- `website/docs/data-sources.mdx` — Section 4: Data sources table
- `website/docs/roadmap.mdx` — Section 5: Roadmap and phase status table
- `website/static/images/architecture.png` — Placeholder architecture diagram image
- `website/static/images/data-flow.png` — Placeholder data-flow diagram image
- `.github/workflows/deploy-docs.yml` — GitHub Actions workflow for GitHub Pages deployment

## Implementation Phases

### Phase 1: Foundation
- Scaffold Docusaurus 3.x project at `website/` with package.json, config, sidebar structure
- Create placeholder images
- Create custom homepage
- Update `.gitignore` for website build artifacts

### Phase 2: Core Implementation
- Write all 5 sections of MDX content (10 content pages total)
- Configure sidebar navigation to match the 5 sections

### Phase 3: Integration & Polish
- Create GitHub Actions deployment workflow
- Validate build succeeds with `npm run build`
- Verify all links, images, and navigation work correctly

## Team Orchestration

- The `/build` command deploys a **self-organizing agent team**. Agents autonomously discover, claim, and execute tasks from a shared task list.
- You are responsible for designing the team composition and task graph so agents can work autonomously.
- IMPORTANT: The plan is the **single source of truth**. `/build` is a pure executor — it does NOT make decisions. Everything must be specified here: team members, task assignments, dependencies, and exhaustive task descriptions.
- Agents cannot ask for clarification mid-task. Every task description must be fully self-contained with all context needed for autonomous execution.

### Team Members

- Builder
  - Name: builder-1
  - Role: Docusaurus scaffold, configuration, homepage, sidebar, placeholder images, GitHub Actions workflow, .gitignore update
  - Agent Type: general-purpose
- Builder
  - Name: builder-2
  - Role: All MDX content pages (Sections 1-5: What is Aegis, How It Works, Architecture, Data Sources, Roadmap)
  - Agent Type: general-purpose
- Validator
  - Name: validator
  - Role: Validates all acceptance criteria and runs validation commands
  - Agent Type: validator

## Step by Step Tasks

- These tasks are executed by self-organizing agents. Agents discover and claim tasks autonomously from the shared task list.
- Each task maps directly to a `TaskCreate` call made by `/build`.
- Task descriptions must be **exhaustive** — agents cannot ask for clarification. Include ALL context: file paths, code patterns, acceptance criteria, and validation commands.
- Start with foundational work, then core implementation, then validation.

### 1. Scaffold Docusaurus Project

- **Task ID**: scaffold-docusaurus
- **Role**: builder
- **Depends On**: none
- **Assigned To**: builder-1
- **Description**: |
    Initialize a Docusaurus 3.x project at `website/` inside the aegis repo. This is a documentation-only site — no blog, no versioning, no i18n.

    ## What to do

    1. Create the `website/` directory at the repo root (`/Users/anvith/aegis/website/`).

    2. Create `website/package.json` with the following content:
       ```json
       {
         "name": "aegis-docs",
         "version": "0.0.0",
         "private": true,
         "scripts": {
           "docusaurus": "docusaurus",
           "start": "docusaurus start",
           "build": "docusaurus build",
           "swizzle": "docusaurus swizzle",
           "deploy": "docusaurus deploy",
           "clear": "docusaurus clear",
           "serve": "docusaurus serve"
         },
         "dependencies": {
           "@docusaurus/core": "^3.7.0",
           "@docusaurus/preset-classic": "^3.7.0",
           "@mdx-js/react": "^3.0.0",
           "clsx": "^2.1.0",
           "prism-react-renderer": "^2.3.0",
           "react": "^18.2.0",
           "react-dom": "^18.2.0"
         },
         "devDependencies": {
           "@docusaurus/module-type-aliases": "^3.7.0",
           "@docusaurus/tsconfig": "^3.7.0",
           "@docusaurus/types": "^3.7.0",
           "typescript": "~5.5.0"
         },
         "browserslist": {
           "production": [">0.5%", "not dead", "not op_mini all"],
           "development": ["last 3 chrome version", "last 3 firefox version", "last 5 safari version"]
         },
         "engines": {
           "node": ">=18.0"
         }
       }
       ```

    3. Create `website/tsconfig.json`:
       ```json
       {
         "extends": "@docusaurus/tsconfig",
         "compilerOptions": {
           "baseUrl": "."
         }
       }
       ```

    4. Create `website/docusaurus.config.ts`:
       ```typescript
       import {themes as prismThemes} from 'prism-react-renderer';
       import type {Config} from '@docusaurus/types';
       import type * as Preset from '@docusaurus/preset-classic';

       const config: Config = {
         title: 'Aegis',
         tagline: 'Internal researcher-ranking engine',
         favicon: 'img/favicon.ico',

         url: 'https://anvithv.github.io',
         baseUrl: '/aegis/',

         organizationName: 'AnvithV',
         projectName: 'aegis',

         onBrokenLinks: 'throw',
         onBrokenMarkdownLinks: 'warn',

         i18n: {
           defaultLocale: 'en',
           locales: ['en'],
         },

         presets: [
           [
             'classic',
             {
               docs: {
                 sidebarPath: './sidebars.ts',
                 editUrl: 'https://github.com/AnvithV/aegis/tree/main/website/',
               },
               blog: false,
               theme: {
                 customCss: './src/css/custom.css',
               },
             } satisfies Preset.Options,
           ],
         ],

         themeConfig: {
           navbar: {
             title: 'Aegis',
             items: [
               {
                 type: 'docSidebar',
                 sidebarId: 'docs',
                 position: 'left',
                 label: 'Documentation',
               },
               {
                 href: 'https://github.com/AnvithV/aegis',
                 label: 'GitHub',
                 position: 'right',
               },
             ],
           },
           footer: {
             style: 'dark',
             links: [
               {
                 title: 'Docs',
                 items: [
                   {label: 'What is Aegis?', to: '/docs/what-is-aegis'},
                   {label: 'How It Works', to: '/docs/how-it-works/data-pipeline'},
                   {label: 'Architecture', to: '/docs/architecture/overview'},
                 ],
               },
               {
                 title: 'More',
                 items: [
                   {label: 'GitHub', href: 'https://github.com/AnvithV/aegis'},
                 ],
               },
             ],
             copyright: `Copyright © ${new Date().getFullYear()} Aegis. Internal use only.`,
           },
           prism: {
             theme: prismThemes.github,
             darkTheme: prismThemes.dracula,
           },
         } satisfies Preset.ThemeConfig,
       };

       export default config;
       ```

    5. Create `website/sidebars.ts`:
       ```typescript
       import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

       const sidebars: SidebarsConfig = {
         docs: [
           {
             type: 'doc',
             id: 'what-is-aegis',
             label: 'What is Aegis?',
           },
           {
             type: 'category',
             label: 'How It Works',
             collapsed: false,
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
             collapsed: false,
             items: [
               'architecture/overview',
               'architecture/diagrams',
             ],
           },
           {
             type: 'doc',
             id: 'data-sources',
             label: 'Data Sources',
           },
           {
             type: 'doc',
             id: 'roadmap',
             label: 'Roadmap',
           },
         ],
       };

       export default sidebars;
       ```

    6. Create `website/src/css/custom.css`:
       ```css
       /**
        * Aegis docs — custom theme overrides.
        * Keeping it minimal; the default Docusaurus classic theme is fine.
        */

       :root {
         --ifm-color-primary: #1a73e8;
         --ifm-color-primary-dark: #1765d0;
         --ifm-color-primary-darker: #155fc4;
         --ifm-color-primary-darkest: #114ea2;
         --ifm-color-primary-light: #2d80ea;
         --ifm-color-primary-lighter: #3988eb;
         --ifm-color-primary-lightest: #5d9fef;
         --ifm-code-font-size: 95%;
         --docusaurus-highlighted-code-line-bg: rgba(0, 0, 0, 0.1);
       }

       [data-theme='dark'] {
         --ifm-color-primary: #5d9fef;
         --ifm-color-primary-dark: #3d8beb;
         --ifm-color-primary-darker: #2d80ea;
         --ifm-color-primary-darkest: #1167d5;
         --ifm-color-primary-light: #7db3f3;
         --ifm-color-primary-lighter: #8dbcf4;
         --ifm-color-primary-lightest: #bdd8f9;
         --docusaurus-highlighted-code-line-bg: rgba(0, 0, 0, 0.3);
       }
       ```

    7. Create `website/src/pages/index.tsx` — a custom homepage with a hero section and 3 feature cards:
       ```tsx
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
             'Aegis scores and ranks researchers across translational, drug-discovery, and clinician populations using a multi-component formula with recency, quality, and topical fit.',
         },
         {
           title: 'Evidence-Backed',
           description:
             'Every ranked candidate comes with a full evidence trail drawn from ~25 data sources including PubMed, patents, grants, clinical trials, and integrity databases.',
         },
         {
           title: 'Continuously Learning',
           description:
             'Downstream task quality feeds back into weight relearning weekly, so ranking accuracy improves over time as more labeling outcomes are collected.',
         },
       ];

       function Feature({title, description}: {title: string; description: string}) {
         return (
           <div className={clsx('col col--4')}>
             <div className="text--center padding-horiz--md padding-vert--lg">
               <Heading as="h3">{title}</Heading>
               <p>{description}</p>
             </div>
           </div>
         );
       }

       export default function Home(): JSX.Element {
         const {siteConfig} = useDocusaurusContext();
         return (
           <Layout
             title={siteConfig.title}
             description="Documentation for Aegis, an internal researcher-ranking engine">
             <HomepageHeader />
             <main>
               <section className="padding-vert--xl">
                 <div className="container">
                   <div className="row">
                     {features.map((props, idx) => (
                       <Feature key={idx} {...props} />
                     ))}
                   </div>
                 </div>
               </section>
             </main>
           </Layout>
         );
       }
       ```

    8. Create `website/src/pages/index.module.css`:
       ```css
       .heroBanner {
         padding: 4rem 0;
         text-align: center;
         position: relative;
         overflow: hidden;
       }

       .buttons {
         display: flex;
         align-items: center;
         justify-content: center;
       }
       ```

    9. Create the docs directory structure:
       ```
       website/docs/
       website/docs/how-it-works/
       website/docs/architecture/
       ```

    10. Create the static images directory:
        ```
        website/static/images/
        website/static/img/
        ```

    11. Run `cd /Users/anvith/aegis/website && npm install` to install dependencies and generate `package-lock.json`.

    ## Files to create
    - `website/package.json`
    - `website/tsconfig.json`
    - `website/docusaurus.config.ts`
    - `website/sidebars.ts`
    - `website/src/css/custom.css`
    - `website/src/pages/index.tsx`
    - `website/src/pages/index.module.css`

    ## Files to modify
    - None

    ## Code patterns to follow
    - Use TypeScript for all configuration files (docusaurus.config.ts, sidebars.ts)
    - Follow Docusaurus 3.x conventions (classic preset, TypeScript config)
    - Minimal customization — default theme is fine

    ## Acceptance criteria
    - `website/package.json` exists with Docusaurus 3.x dependencies
    - `website/docusaurus.config.ts` exists with correct site URL, baseUrl, and preset configuration
    - `website/sidebars.ts` exists with the 5-section structure
    - `website/src/pages/index.tsx` exists with homepage component
    - `website/src/css/custom.css` exists with theme colors
    - `website/node_modules/` exists (npm install succeeded)
    - Directory structure created: `website/docs/`, `website/docs/how-it-works/`, `website/docs/architecture/`, `website/static/images/`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/website && test -f package.json && test -f docusaurus.config.ts && test -f sidebars.ts && test -f tsconfig.json && test -f src/pages/index.tsx && test -f src/css/custom.css && test -d node_modules && test -d docs && test -d docs/how-it-works && test -d docs/architecture && test -d static/images && echo "Scaffold OK"
    ```

### 2. Create Placeholder Images and Update .gitignore

- **Task ID**: placeholder-images
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-1
- **Description**: |
    Create placeholder images for the architecture and data-flow diagrams, and update the repo .gitignore for website build artifacts.

    ## What to do

    1. Create `website/static/images/architecture.png` — a placeholder PNG image. Since we need a real PNG file (not SVG), generate a minimal valid 1x1 white PNG using a simple binary approach. Use this bash command to create a minimal placeholder:
       ```bash
       cd /Users/anvith/aegis/website/static/images && python3 -c "
       import struct, zlib
       def create_png(width, height, text=''):
           # Minimal PNG: white rectangle
           raw_data = b''
           for y in range(height):
               raw_data += b'\x00' + b'\xff\xff\xff' * width
           compressed = zlib.compress(raw_data)

           def chunk(chunk_type, data):
               c = chunk_type + data
               return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

           ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
           return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

       with open('architecture.png', 'wb') as f:
           f.write(create_png(800, 400))
       with open('data-flow.png', 'wb') as f:
           f.write(create_png(800, 400))
       print('Placeholder PNGs created')
       "
       ```

       Alternatively, if the Python approach is problematic, create simple SVG files instead and rename them:

       Create `website/static/images/architecture.png` — if the PNG generation fails, create an SVG at `website/static/images/architecture.svg` with this content and reference it from the MDX as `.svg`:
       ```svg
       <svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
         <rect width="800" height="400" fill="#f0f0f0" rx="8"/>
         <text x="400" y="180" text-anchor="middle" font-family="system-ui, sans-serif" font-size="24" fill="#666">Architecture Diagram</text>
         <text x="400" y="220" text-anchor="middle" font-family="system-ui, sans-serif" font-size="14" fill="#999">To be created in Excalidraw / Figma</text>
       </svg>
       ```

       Create `website/static/images/data-flow.svg` similarly:
       ```svg
       <svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
         <rect width="800" height="400" fill="#f0f0f0" rx="8"/>
         <text x="400" y="180" text-anchor="middle" font-family="system-ui, sans-serif" font-size="24" fill="#666">Data Flow Diagram</text>
         <text x="400" y="220" text-anchor="middle" font-family="system-ui, sans-serif" font-size="14" fill="#999">To be created in Excalidraw / Figma</text>
       </svg>
       ```

       **Preferred approach**: Use SVG files since they are text-based and easy to create. Name them `.svg` and reference them as `/images/architecture.svg` and `/images/data-flow.svg` in the MDX content. Make sure to tell builder-2 (in the diagrams.mdx content below in task 8) to reference `.svg` if SVGs are created, or `.png` if PNGs are created.

       **IMPORTANT**: Create BOTH `.png` AND `.svg` versions. The `.png` can be the Python-generated minimal white placeholder, and the `.svg` is the descriptive placeholder. The MDX content in task 8 will reference the `.png` files as specified in the user requirements. If the Python PNG generation fails, just create the SVGs and update the image references in the MDX to point to `.svg` instead.

    2. Create `website/static/img/` directory and add a simple `favicon.ico`. Since we need a favicon, create a minimal one:
       ```bash
       # Create a minimal favicon (1x1 pixel ICO)
       cd /Users/anvith/aegis/website/static/img && python3 -c "
       # Minimal ICO file (1x1 pixel, blue)
       import struct
       ico = bytearray()
       # ICO header: reserved=0, type=1 (ICO), count=1
       ico += struct.pack('<HHH', 0, 1, 1)
       # Directory entry: 16x16, 0 colors, 0 reserved, 1 plane, 32 bpp
       bmp_size = 40 + 16*16*4 + 16*4  # header + pixels + mask
       ico += struct.pack('<BBBBHHIH', 16, 16, 0, 0, 1, 32, bmp_size, 22)
       # BMP info header
       ico += struct.pack('<IiiHHIIiiII', 40, 16, 32, 1, 32, 0, 16*16*4+16*4, 0, 0, 0, 0)
       # Pixel data (blue, bottom-up)
       for y in range(16):
           for x in range(16):
               ico += struct.pack('<BBBB', 232, 115, 26, 255)  # BGRA (Aegis blue=#1a73e8)
       # AND mask (all 0 = fully opaque)
       ico += b'\x00' * (16 * 4)
       with open('favicon.ico', 'wb') as f:
           f.write(bytes(ico))
       print('favicon created')
       "
       ```

       If the Python favicon approach fails, just skip it — Docusaurus will show a default favicon and the build will still succeed.

    3. Update the repo root `.gitignore` at `/Users/anvith/aegis/.gitignore` to add website build artifacts. Append these lines at the end of the file:
       ```
       # Docusaurus
       website/node_modules/
       website/.docusaurus/
       website/build/
       ```

       **IMPORTANT**: Read the existing `.gitignore` first, then append the new lines. The current file ends with:
       ```
       # mypy
       .mypy_cache/
       ```
       Add a blank line and then the Docusaurus section after that.

    ## Files to create
    - `website/static/images/architecture.png` (or `.svg` if PNG generation fails)
    - `website/static/images/data-flow.png` (or `.svg` if PNG generation fails)
    - `website/static/img/favicon.ico` (best effort)

    ## Files to modify
    - `/Users/anvith/aegis/.gitignore` — append Docusaurus ignore rules

    ## Code patterns to follow
    - Placeholder images should clearly indicate they are placeholders
    - SVG is preferred for placeholder readability

    ## Acceptance criteria
    - Placeholder image files exist at `website/static/images/architecture.png` (or `.svg`) and `website/static/images/data-flow.png` (or `.svg`)
    - `.gitignore` includes entries for `website/node_modules/`, `website/.docusaurus/`, `website/build/`
    - `website/static/img/` directory exists

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && (test -f website/static/images/architecture.png || test -f website/static/images/architecture.svg) && (test -f website/static/images/data-flow.png || test -f website/static/images/data-flow.svg) && grep -q "website/node_modules" .gitignore && grep -q "website/.docusaurus" .gitignore && grep -q "website/build" .gitignore && echo "Placeholders and gitignore OK"
    ```

### 3. Write Section 1 — What is Aegis?

- **Task ID**: content-what-is-aegis
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-2
- **Description**: |
    Write the "What is Aegis?" page — Section 1 of the documentation. This is the entry point for all readers. It explains the problem Aegis solves, what it produces, who uses it, the scoring formula in plain English, and the three researcher populations.

    ## What to do

    1. Create `website/docs/what-is-aegis.mdx` with the following content structure. Write the full MDX file with all content inline — do NOT use placeholder text. The content must be complete and ready for readers.

       The file must start with frontmatter:
       ```yaml
       ---
       sidebar_position: 1
       title: What is Aegis?
       description: An overview of Aegis, the internal researcher-ranking engine — what it solves, what it produces, and who uses it.
       ---
       ```

       Then write the following sections in MDX:

       **Opening paragraph**: Aegis is an internal researcher-ranking engine. It takes a natural-language description of a labeling task (e.g., "Rank oncologists with expertise in non-small-cell lung cancer immunotherapy") and returns a ranked list of researcher candidates with scores and full evidence trails. Internal task managers use these ranked lists to select researchers for labeling, review, and advisory tasks.

       **The problem it solves**: When building labeling panels for healthcare and life-science tasks, finding the right researchers is hard. There are millions of researchers worldwide, spread across publications, patents, grants, clinical trials, and regulatory databases. Aegis automates the discovery and ranking process by ingesting data from ~25 sources, resolving researcher identities, and scoring each candidate on recency, quality, and topical fit relative to the query.

       **What it produces**: For each query, Aegis returns:
       - A ranked list of K candidates (configurable, default 20)
       - Per-candidate composite scores with component breakdown (Recency, Quality, Topical Fit, Integrity)
       - Full evidence trails: which publications, patents, grants, trials, and credentials contributed to each score
       - Integrity flags: whether the candidate was discounted or disqualified (and why)

       **Who uses it**: Internal task managers who need to assemble researcher panels. Aegis is not researcher-facing — researchers do not see their scores or rankings.

       **The scoring formula (plain English)**: Aegis computes a score for each candidate `c` against a query `q`. The formula has four components:
       - **Recency (R)**: How recently has this researcher published, patented, or received grants in the query's topic area? A researcher who published a relevant paper last month scores higher on recency than one whose last relevant paper was five years ago.
       - **Quality (Q)**: What is this researcher's overall quality prior, independent of the specific query? This includes field-normalized citation impact, the scale and consistency of their funding, leadership positions (department chair, center director), translational activity (bench-to-bedside indicators), and academic lineage.
       - **Topical Fit (C)**: How well does this researcher's body of work match the specific query? Aegis converts both the query and each candidate's publication/patent/grant portfolio into MeSH (Medical Subject Heading) vectors and measures similarity.
       - **Integrity (I)**: Has this researcher been flagged by any integrity source? Hard disqualifiers (retractions, ORI findings, OFAC/SAM sanctions) zero out the score entirely. Soft signals (predatory journal publications, paper-mill indicators) apply multiplicative discounts.

       The final score combines these: the integrity gate acts as a multiplier (1.0 for clean candidates, 0.0 for hard-disqualified, somewhere in between for soft-discounted), and the three scored components (Recency, Quality, Topical Fit) are weighted and combined. The weights are learned from downstream task outcomes — they are not hand-tuned.

       **The three researcher populations**: Aegis handles three distinct populations, each with different data sources and scoring emphasis:
       - **Translational**: Academic researchers whose work spans bench-to-bedside. Primary data sources: PubMed publications, NIH/ERC/MRC/CIHR grants, clinical trial registrations. Scoring emphasizes publication impact (RCR), grant funding trajectory, and translational indicators.
       - **Drug Discovery**: Medicinal chemists and drug-discovery scientists. Primary data sources: USPTO and EPO patents, ChEMBL bioactivity data, patent-grant linkage. Scoring emphasizes patent portfolio (forward citations, family breadth, maintenance status) and chemistry-relevant publication output.
       - **Clinician**: Practicing physicians linked to NPI identifiers. Primary data sources: NPPES/NPI registry, ABMS board certifications, state medical board licenses, CMS Medicare utilization data, USNWR hospital tier. Scoring emphasizes board certification status, hospital affiliation tier, and procedure volume.

       Each population has its own weight vector (alpha, beta, gamma for R, Q, C) learned independently from population-specific audit panels.

    ## Files to create
    - `website/docs/what-is-aegis.mdx`

    ## Files to modify
    - None

    ## Code patterns to follow
    - MDX format with YAML frontmatter
    - Use `##` for major sections, `###` for subsections
    - Use bullet lists for structured information
    - Write in plain English — no math notation, no code snippets
    - Target audience: engineers joining the team AND internal stakeholders/leadership
    - Tone: clear, direct, professional. Not academic, not marketing.

    ## Acceptance criteria
    - `website/docs/what-is-aegis.mdx` exists
    - File has YAML frontmatter with `sidebar_position: 1` and `title: What is Aegis?`
    - Contains sections: problem it solves, what it produces, who uses it, scoring formula in plain English, three populations
    - Scoring formula explained conceptually (R, Q, C, I) without math notation
    - Three populations (translational, drug-discovery, clinician) described with their data sources and scoring emphasis
    - File is valid MDX (no JSX syntax errors)

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/what-is-aegis.mdx && grep -q "sidebar_position: 1" website/docs/what-is-aegis.mdx && grep -q "Recency" website/docs/what-is-aegis.mdx && grep -q "Quality" website/docs/what-is-aegis.mdx && grep -q "Topical Fit" website/docs/what-is-aegis.mdx && grep -q "Integrity" website/docs/what-is-aegis.mdx && grep -q "Translational" website/docs/what-is-aegis.mdx && grep -q "Drug Discovery" website/docs/what-is-aegis.mdx && grep -q "Clinician" website/docs/what-is-aegis.mdx && echo "Section 1 OK"
    ```

### 4. Write Section 2 — How It Works (5 pages)

- **Task ID**: content-how-it-works
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-2
- **Description**: |
    Write the 5 pages of Section 2 — "How It Works". These pages explain the internal mechanisms of Aegis at a conceptual level. No code snippets, no API references — plain English explanations.

    ## What to do

    Create 5 MDX files under `website/docs/how-it-works/`. Each file must have YAML frontmatter with `sidebar_position` for ordering within the category.

    ### File 1: `website/docs/how-it-works/data-pipeline.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 1
    title: Data Pipeline
    description: Where researcher data comes from and how it stays fresh.
    ---
    ```

    Content to cover:
    - **Source breadth**: Aegis ingests researcher data from approximately 25 sources spanning publications, grants, patents, clinical trials, clinician registries, integrity databases, and taxonomy cross-walks.
    - **Ingestion cadence** — three tiers:
      - **Event-driven (< 6 hours)**: Integrity sources (Retraction Watch, ORI, OFAC/SAM, LEIE). These are the highest priority because a retraction or sanction must immediately affect rankings.
      - **Daily**: Preprint servers (bioRxiv, medRxiv). New preprints drop daily and are indexed overnight.
      - **Weekly**: Most other sources — PubMed, NIH RePORTER, ClinicalTrials.gov, USPTO, EPO, NPPES, etc. Full incremental refresh on a weekly schedule.
    - **Ingestion architecture**: Each source has a typed API client that returns structured Pydantic records. Clients use httpx with retry policies and rate limiting. Raw records flow through identity resolution before storage. DuckDB is the analytical store.
    - **Data freshness**: The system tracks ingestion timestamps per source. Stale-source alerts fire if a source hasn't been refreshed within 2x its expected cadence.

    ### File 2: `website/docs/how-it-works/identity-resolution.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 2
    title: Identity Resolution
    description: How Aegis knows two records are the same person.
    ---
    ```

    Content to cover:
    - **The problem**: A single researcher may appear as "Jane Smith" in PubMed, "J. Smith" on a patent, "Jane A. Smith, MD" in the NPI registry, and "Smith, JA" in a grant database. Aegis must recognize these as the same person.
    - **Deterministic linking**: When authoritative identifiers are present, linking is straightforward:
      - ORCID: A researcher's ORCID iD is a globally unique identifier. If two records share an ORCID, they are the same person.
      - NPI: For clinicians, the National Provider Identifier is unique and permanent.
      - ROR: Research Organization Registry IDs normalize institutional affiliations (e.g., "Harvard Medical School" and "HMS" resolve to the same ROR ID).
    - **Probabilistic linking**: When no shared identifier exists, Aegis uses probabilistic record linkage:
      - Name similarity (accounting for initials, middle names, transliteration of non-Latin names)
      - Institutional affiliation overlap
      - Co-authorship patterns
      - Temporal consistency (a researcher's career timeline should be plausible)
      - The linker produces a confidence score; matches above 0.95 are auto-merged, matches between 0.80 and 0.95 are flagged for review.
    - **Cross-population merge**: A researcher might be both a translational scientist (PubMed papers) and a clinician (NPI record). The identity resolution layer can merge records across populations when the evidence is strong enough.

    ### File 3: `website/docs/how-it-works/integrity-gate.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 3
    title: Integrity Gate
    description: What disqualifies or discounts a researcher.
    ---
    ```

    Content to cover:
    - **Purpose**: Before scoring, every candidate passes through the integrity gate. This protects downstream labeling quality by excluding compromised researchers and discounting those with integrity concerns.
    - **Hard disqualifiers** — these zero out the candidate's score entirely:
      - **Retraction**: A first- or last-author retraction flagged in Retraction Watch. The candidate's score becomes 0.
      - **ORI finding**: An Office of Research Integrity misconduct finding.
      - **OFAC/SAM sanction**: The candidate appears on the OFAC Specially Designated Nationals list or the SAM exclusion list.
      - **LEIE exclusion**: Listed on the HHS/OIG List of Excluded Individuals/Entities.
    - **Soft signals** — these apply multiplicative discounts (the candidate still appears in rankings, but with a reduced score):
      - **Predatory journal publications**: If a significant fraction of a candidate's recent publications are in journals flagged as predatory.
      - **Paper-mill indicators**: Statistical patterns in authorship, submission timing, or figure similarity that suggest paper-mill involvement.
      - **Citation manipulation**: Unusual self-citation patterns or citation rings detected by iCite analysis.
    - **Contestability**: Candidates (or their institutions) can contest an integrity flag. A contestability workflow allows overrides with documented justification. Overridden flags are retained in the audit log but no longer affect scoring.
    - **Transparency**: Every integrity decision is logged. When a candidate is discounted or disqualified, the evidence trail shows exactly which source triggered the flag and what discount was applied.

    ### File 4: `website/docs/how-it-works/scoring.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 4
    title: Scoring Components
    description: How Aegis scores each candidate — Recency, Quality, and Topical Fit explained.
    ---
    ```

    Content to cover:
    - **Overview**: After passing the integrity gate, each candidate is scored on three dimensions relative to the query. These scores are combined using learned weights to produce a final ranking.
    - **Recency (R)**: Measures how current the candidate's work is in the query's topic area.
      - Looks at the dates of the candidate's publications, patents, and grants that are topically relevant to the query.
      - More recent relevant work scores higher. A candidate who published a relevant paper last month scores higher than one whose last relevant paper was three years ago.
      - Uses an exponential decay function — recent work gets full credit, older work gets progressively less.
      - This is query-dependent: a candidate might have very recent work in oncology but nothing recent in cardiology.
    - **Quality Prior (Q)**: A query-independent assessment of the candidate's overall research caliber. Composed of several sub-scores:
      - **Citation impact**: Field-normalized citation rates (using iCite's Relative Citation Ratio). A paper cited 10x the field average contributes more than one cited at the average rate.
      - **Funding**: Grant funding trajectory — the number, recency, and size of grants. Consistent multi-year funding from major agencies (NIH, ERC) signals sustained research capacity.
      - **Leadership**: Institutional positions (department chair, center director, program leader) extracted from affiliation records and grant PI designations.
      - **Translational activity**: Evidence of bench-to-bedside work — papers linked to clinical trials, patents filed alongside publications, clinical advisory roles.
      - **Academic lineage**: Mentor-mentee relationships and training pedigree (e.g., trained in a top-tier lab).
    - **Topical Fit (C)**: Measures how well the candidate's body of work aligns with the specific query.
      - The query is expanded into MeSH (Medical Subject Heading) descriptors using LLM-assisted query expansion. For example, "NSCLC immunotherapy" expands to MeSH terms like "Carcinoma, Non-Small-Cell Lung", "Immunotherapy", "Immune Checkpoint Inhibitors", etc.
      - Each candidate's portfolio (publications, patents, grants) is also represented as a MeSH vector — a weighted list of MeSH terms based on what they have worked on.
      - Topical fit is the similarity between the query's MeSH vector and the candidate's MeSH vector.
      - This is the most query-specific component. A world-class cardiologist scores low on topical fit for an oncology query.
    - **Weight learning**: The weights (alpha for R, beta for Q, gamma for C) are not hand-tuned. They are learned from downstream task outcomes using Plackett-Luce models fitted on pairwise audit judgments. The weights are relearned weekly as new outcome data flows in. Each population has its own weight vector.

    ### File 5: `website/docs/how-it-works/feedback-loop.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 5
    title: Feedback Loop
    description: How downstream task quality feeds back into Aegis.
    ---
    ```

    Content to cover:
    - **The loop**: Aegis does not operate in isolation. When ranked candidates are selected for labeling tasks, the quality of their work feeds back into Aegis to improve future rankings.
    - **What is measured**: Two primary signals:
      - **Fleiss kappa**: Inter-annotator agreement on the labeling task. Higher kappa means the selected researchers produced more consistent labels, suggesting the panel was well-composed.
      - **Accept rate**: What fraction of the selected researchers' work was accepted without revision? Higher accept rates suggest better-qualified panelists.
    - **How it feeds back**: These quality signals are aggregated weekly and used to refit the scoring weights (alpha, beta, gamma) via Plackett-Luce optimization. If downstream outcomes improve when recency-weighted candidates are selected, the recency weight increases.
    - **Cold start**: When a new population or query type has insufficient outcome data, Aegis uses prior weights derived from expert judgment in initial audit panels. As real outcome data accumulates, the learned weights gradually take over.
    - **Guardrails**: Weight relearning includes convergence checks and stability monitoring. If new weights would cause a dramatic shift in rankings (measured by rank-order correlation with previous weights), the system flags the change for human review before applying it.

    ## Files to create
    - `website/docs/how-it-works/data-pipeline.mdx`
    - `website/docs/how-it-works/identity-resolution.mdx`
    - `website/docs/how-it-works/integrity-gate.mdx`
    - `website/docs/how-it-works/scoring.mdx`
    - `website/docs/how-it-works/feedback-loop.mdx`

    ## Files to modify
    - None

    ## Code patterns to follow
    - MDX format with YAML frontmatter including `sidebar_position` and `title`
    - Use `##` for major sections, `###` for subsections
    - Use bullet lists and bold terms for key concepts
    - Write in plain English — no math notation, no code snippets, no file paths
    - Conceptual explanations aimed at engineers joining the team and internal stakeholders

    ## Acceptance criteria
    - All 5 files exist under `website/docs/how-it-works/`
    - Each file has correct YAML frontmatter with `sidebar_position` (1-5) and `title`
    - data-pipeline.mdx covers: ~25 sources, three ingestion cadence tiers, event-driven for integrity
    - identity-resolution.mdx covers: ORCID, NPI, ROR, probabilistic linking, cross-population merge
    - integrity-gate.mdx covers: hard disqualifiers (retraction, ORI, OFAC/SAM), soft signals, contestability
    - scoring.mdx covers: R (recency), Q (quality with sub-scores), C (topical fit with MeSH vectors), weight learning
    - feedback-loop.mdx covers: Fleiss kappa, accept rate, weekly weight relearning, cold start, guardrails

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/how-it-works/data-pipeline.mdx && test -f website/docs/how-it-works/identity-resolution.mdx && test -f website/docs/how-it-works/integrity-gate.mdx && test -f website/docs/how-it-works/scoring.mdx && test -f website/docs/how-it-works/feedback-loop.mdx && grep -q "sidebar_position: 1" website/docs/how-it-works/data-pipeline.mdx && grep -q "sidebar_position: 5" website/docs/how-it-works/feedback-loop.mdx && grep -q "Retraction Watch" website/docs/how-it-works/integrity-gate.mdx && grep -q "MeSH" website/docs/how-it-works/scoring.mdx && grep -q "Fleiss" website/docs/how-it-works/feedback-loop.mdx && echo "Section 2 OK"
    ```

### 5. Write Section 3 — System Architecture (2 pages)

- **Task ID**: content-architecture
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-2
- **Description**: |
    Write the 2 pages of Section 3 — "System Architecture". These pages describe the phase-by-phase build history and include placeholder diagrams.

    ## What to do

    ### File 1: `website/docs/architecture/overview.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 1
    title: Phase-by-Phase Overview
    description: How Aegis was built across four phases, and what each phase unlocked.
    ---
    ```

    Content to cover — write a section for each phase:

    **Phase 0 — Foundation and Ingestion**:
    - What it built: DuckDB analytical schema for candidate storage, typed source clients for PubMed, ClinicalTrials.gov, and NIH RePORTER, identity resolution pipeline (deterministic + probabilistic), and an NSCLC (non-small-cell lung cancer) seed cohort for validation.
    - What it unlocked: The ability to ingest researcher records from multiple sources, resolve them into unified candidate profiles, and validate against a known expert list. This was the data foundation everything else builds on.

    **Phase 1 — Scoring Engine**:
    - What it built: The full scoring engine with six quality-prior sub-scores (F1 through F7 covering citation impact, funding, leadership, apex recognition, translational activity, and lineage), the integrity gate (hard zeros and soft discounts), Plackett-Luce weight learning from pairwise audit judgments, a bootstrap pairwise audit panel for collecting expert judgments, and score-variance estimation.
    - What it unlocked: End-to-end ranking — given a query, produce a scored and ranked list of candidates with evidence trails and integrity flags.

    **Phase 2 — Multi-Population**:
    - What it built: Drug-discovery population with USPTO and EPO patent ingestion, CPC-to-MeSH and ChEMBL-to-MeSH taxonomy cross-walks. Clinician population with NPI registry, ABMS board certifications, state medical board data (10 states), and USNWR hospital tier rankings. A specialty classifier for automatic population routing. Cross-population identity merge to handle researchers who appear in multiple populations.
    - What it unlocked: Aegis can now rank three distinct researcher types — translational scientists, drug-discovery chemists, and clinicians — each with population-specific data sources and learned weight vectors.

    **Phase 3 — Production API, Continuous Ingestion, and Geographic Broadening**:
    - What it built: Production-grade FastAPI with JWT authentication and audit logging. Event-driven integrity ingestion (< 6h latency for integrity sources). LLM-assisted query expansion for better MeSH vector coverage. Geographic broadening with 7 new non-US source clients (EPO full member-state coverage, ERC, Horizon Europe, MRC, CIHR, JST/KAKEN, NSFC). A contestability workflow for integrity flag overrides. A downstream-quality feedback loop with Fleiss kappa and accept-rate tracking feeding into weekly weight relearning.
    - What it unlocked: A production-ready API that external systems can query, continuous data freshness, global researcher coverage (targeting 40%+ non-US), and a self-improving ranking system.

    **Phase 4 — Frontend** (in progress):
    - What it built: A Next.js web application with three screens: New Query (submit ranking queries), Results (view ranked candidates with score breakdowns and evidence trails), and Query History.
    - What it unlocked: Task managers can interact with Aegis directly through a web interface instead of API calls.

    ### File 2: `website/docs/architecture/diagrams.mdx`

    Frontmatter:
    ```yaml
    ---
    sidebar_position: 2
    title: Architecture Diagrams
    description: High-level architecture and data-flow diagrams.
    ---
    ```

    Content:
    - **High-Level Architecture**: A brief description of the system layers: ingestion layer (source clients) feeds into identity resolution, which feeds into the scoring engine, which feeds into the API layer, which feeds into the frontend. Integrity checking runs as a gate within the scoring pipeline. Include the placeholder image:
      ```mdx
      ![High-level architecture diagram](/images/architecture.png)
      ```
      Add a note: *This diagram is a placeholder. The final version will be created in Excalidraw or Figma.*

    - **Data Flow**: Describe the flow for a single query: query text comes in, LLM expansion converts it to MeSH vectors, the scoring engine retrieves candidates and computes R/Q/C scores, the integrity gate filters and discounts, results are ranked, and the response is returned. Over time, feedback from downstream tasks flows back into weight relearning. Include the placeholder image:
      ```mdx
      ![Data flow diagram](/images/data-flow.png)
      ```
      Add a note: *This diagram is a placeholder. The final version will be created in Excalidraw or Figma.*

    **IMPORTANT about image references**: The placeholder images may be `.png` or `.svg` files. Check what exists in `website/static/images/` before writing the image references. If only `.svg` files exist, use `/images/architecture.svg` and `/images/data-flow.svg`. If `.png` files exist, use `/images/architecture.png` and `/images/data-flow.png`. Default to `.png` in your initial write — the validator or a fix task can correct this if needed.

    ## Files to create
    - `website/docs/architecture/overview.mdx`
    - `website/docs/architecture/diagrams.mdx`

    ## Files to modify
    - None

    ## Code patterns to follow
    - MDX format with YAML frontmatter
    - Use `##` for phase headers, paragraphs for descriptions
    - "What it built" / "What it unlocked" structure for each phase
    - Image syntax: `![alt text](/images/filename.png)`

    ## Acceptance criteria
    - Both files exist under `website/docs/architecture/`
    - overview.mdx covers all 5 phases (0-4) with "built" and "unlocked" descriptions
    - diagrams.mdx includes image references to both placeholder images
    - diagrams.mdx includes placeholder notes about Excalidraw/Figma
    - Phase 0 mentions DuckDB, PubMed, identity resolution, NSCLC seed cohort
    - Phase 1 mentions scoring engine, F1-F7, integrity gate, Plackett-Luce
    - Phase 2 mentions USPTO, EPO, NPI, ABMS, drug-discovery, clinician, specialty classifier
    - Phase 3 mentions FastAPI, JWT, LLM query expansion, geographic broadening, feedback loop
    - Phase 4 mentions Next.js, three screens

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/architecture/overview.mdx && test -f website/docs/architecture/diagrams.mdx && grep -q "Phase 0" website/docs/architecture/overview.mdx && grep -q "Phase 1" website/docs/architecture/overview.mdx && grep -q "Phase 2" website/docs/architecture/overview.mdx && grep -q "Phase 3" website/docs/architecture/overview.mdx && grep -q "Phase 4" website/docs/architecture/overview.mdx && grep -q "architecture" website/docs/architecture/diagrams.mdx && grep -q "data-flow" website/docs/architecture/diagrams.mdx && echo "Section 3 OK"
    ```

### 6. Write Section 4 — Data Sources

- **Task ID**: content-data-sources
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-2
- **Description**: |
    Write the Data Sources page — Section 4 of the documentation. This page contains a comprehensive table of all ~25 data sources organized by category, with details on what each source provides, its refresh cadence, and which population(s) it serves.

    ## What to do

    Create `website/docs/data-sources.mdx` with frontmatter:
    ```yaml
    ---
    sidebar_position: 4
    title: Data Sources
    description: The ~25 data sources Aegis ingests, organized by category with refresh cadence and population coverage.
    ---
    ```

    Content structure:

    **Opening paragraph**: Aegis ingests data from approximately 25 sources across seven categories. Each source is refreshed on a defined cadence and serves one or more of the three researcher populations (Translational, Drug Discovery, Clinician).

    Then create a table for each category. Use MDX/Markdown tables. Each table should have columns: **Source**, **What It Provides**, **Refresh Cadence**, **Population(s)**.

    **Publications**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | PubMed | Indexed biomedical journal articles with MeSH terms, author affiliations, and PMIDs | Weekly | Translational, Clinician |
    | bioRxiv | Biology preprints (pre-peer-review) | Daily | Translational |
    | medRxiv | Medical/clinical preprints (pre-peer-review) | Daily | Translational, Clinician |
    | iCite | Field-normalized citation metrics (Relative Citation Ratio) for PubMed articles | Weekly | Translational |

    **Grants**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | NIH RePORTER | US NIH-funded grants with PI info, project abstracts, funding amounts | Weekly | Translational |
    | ERC (European Research Council) | ERC-funded grants across EU member states | Weekly | Translational |
    | Horizon Europe | EU framework programme grants | Weekly | Translational |
    | MRC (Medical Research Council) | UK MRC-funded grants | Weekly | Translational |
    | CIHR (Canadian Institutes of Health Research) | Canadian health research grants | Weekly | Translational |
    | JST/KAKEN | Japanese government research grants (with name transliteration) | Weekly | Translational |
    | NSFC (National Natural Science Foundation of China) | Chinese government research grants | Weekly | Translational |

    **Patents**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | USPTO PatentsView | US granted patents with inventor attribution, CPC codes, forward citations | Weekly | Drug Discovery |
    | EPO Espacenet | European patents with patent-family deduplication across 39 member states | Weekly | Drug Discovery |
    | WIPO PCT | International patent applications (Patent Cooperation Treaty) | Weekly | Drug Discovery |

    **Clinical**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | ClinicalTrials.gov | Clinical trial registrations with investigator roles | Weekly | Translational, Clinician |
    | CMS Medicare Utilization | Medicare claims-based procedure volumes by provider | Weekly | Clinician |

    **Clinician**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | NPPES/NPI | National Provider Identifier registry — unique clinician identifiers, practice addresses, specialties | Weekly | Clinician |
    | ABMS | American Board of Medical Specialties board certification status | Weekly | Clinician |
    | State Medical Boards (10 states) | Active medical license status and disciplinary actions | Weekly | Clinician |
    | USNWR Hospital Tier | US News hospital ranking tiers for institutional affiliation quality signals | Monthly | Clinician |

    **Integrity**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | Retraction Watch | Retracted publications with reason codes | Event-driven (< 6h) | All |
    | ORI (Office of Research Integrity) | Federal research misconduct findings | Event-driven (< 6h) | All |
    | OFAC/SAM | Treasury sanctions and federal exclusion lists | Event-driven (< 6h) | All |
    | LEIE | HHS/OIG excluded individuals and entities | Event-driven (< 6h) | All |

    **Taxonomy / Cross-walks**:
    | Source | What It Provides | Refresh Cadence | Population(s) |
    |--------|-----------------|-----------------|---------------|
    | ChEMBL | Bioactivity database for target-to-MeSH mapping in chemistry queries | Monthly | Drug Discovery |
    | ICD-10/CPT-MeSH cross-walk | Maps clinical procedure and diagnosis codes to MeSH descriptors | Quarterly | Clinician |
    | CPC-MeSH cross-walk | Maps patent classification codes (CPC/IPC) to MeSH descriptors | Quarterly | Drug Discovery |

    **Note on geographic coverage**: After this section, include a paragraph:
    At the end of Phase 2, approximately 15% of candidates in the Aegis database were non-US researchers. Phase 3's geographic broadening (adding ERC, Horizon Europe, MRC, CIHR, KAKEN, NSFC, and full EPO member-state coverage) targets 40% or greater non-US representation.

    ## Files to create
    - `website/docs/data-sources.mdx`

    ## Files to modify
    - None

    ## Code patterns to follow
    - MDX format with YAML frontmatter
    - Use Markdown tables (not HTML tables)
    - Group tables by category with `##` headers
    - Include the geographic coverage note at the end

    ## Acceptance criteria
    - `website/docs/data-sources.mdx` exists
    - File has YAML frontmatter with `sidebar_position: 4` and `title: Data Sources`
    - Contains 7 category tables: Publications, Grants, Patents, Clinical, Clinician, Integrity, Taxonomy
    - Each table has columns: Source, What It Provides, Refresh Cadence, Population(s)
    - Lists approximately 25 sources total
    - Integrity sources show "Event-driven (< 6h)" cadence
    - Geographic coverage note mentions 15% and 40%+ targets

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/data-sources.mdx && grep -q "sidebar_position: 4" website/docs/data-sources.mdx && grep -q "PubMed" website/docs/data-sources.mdx && grep -q "USPTO" website/docs/data-sources.mdx && grep -q "NPPES" website/docs/data-sources.mdx && grep -q "Retraction Watch" website/docs/data-sources.mdx && grep -q "ChEMBL" website/docs/data-sources.mdx && grep -q "Event-driven" website/docs/data-sources.mdx && grep -q "40%" website/docs/data-sources.mdx && echo "Section 4 OK"
    ```

### 7. Write Section 5 — Roadmap

- **Task ID**: content-roadmap
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-2
- **Description**: |
    Write the Roadmap page — Section 5 of the documentation. This page shows what has been built, what is in progress, and what comes next.

    ## What to do

    Create `website/docs/roadmap.mdx` with frontmatter:
    ```yaml
    ---
    sidebar_position: 5
    title: Roadmap
    description: What has been built, what is in progress, and what comes next for Aegis.
    ---
    ```

    Content structure:

    **Opening paragraph**: Aegis has been built across four phases, with a fifth underway. This page summarizes the status of each phase and outlines what comes next.

    **Phase status table**:
    | Phase | Name | Status | Key Deliverable |
    |-------|------|--------|----------------|
    | 0 | Foundation & Ingestion | Complete | DuckDB schema, PubMed/RePORTER/CT.gov clients, identity resolution, NSCLC seed cohort |
    | 1 | Scoring Engine | Complete | Full quality prior (F1-F7), integrity gate, Plackett-Luce weight learning, pairwise audit panel |
    | 2 | Multi-Population | Complete | Drug-discovery population (patents), clinician population (NPI/ABMS), specialty classifier, cross-population merge |
    | 3 | Production & Broadening | Complete | FastAPI + JWT auth, event-driven integrity ingestion, LLM query expansion, geographic broadening, feedback loop, contestability |
    | 4 | Frontend | In Progress | Next.js dashboard (New Query, Results, Query History) |

    **What has been built** (brief summary): Phases 0 through 3 are complete. Aegis can ingest data from ~25 sources, resolve identities across populations, score and rank candidates on three dimensions with integrity gating, serve rankings via a production API with authentication and audit logging, and improve its own weights from downstream task outcomes.

    **What is in progress**: Phase 4 — the Next.js frontend. This gives task managers a web interface for submitting queries, viewing ranked results with score breakdowns and evidence trails, and browsing query history. The frontend communicates with the existing Aegis backend API via server-side proxied routes.

    **What comes next**:
    - **Additional populations**: Expanding beyond translational, drug-discovery, and clinician to cover new researcher types such as AI/ML researchers, biostatisticians, and regulatory affairs specialists.
    - **Deeper geographic coverage**: Continuing to add non-US data sources and improve the international researcher base toward 50%+ non-US representation.
    - **Code and dataset artifacts**: Scoring researchers on their open-source code contributions (GitHub, GitLab) and published datasets (Zenodo, Figshare, GEO).
    - **Enhanced feedback integration**: Richer feedback signals beyond Fleiss kappa and accept rate — e.g., time-to-completion, revision depth, and domain-expert assessments of annotation quality.

    ## Files to create
    - `website/docs/roadmap.mdx`

    ## Files to modify
    - None

    ## Code patterns to follow
    - MDX format with YAML frontmatter
    - Use a Markdown table for the phase status overview
    - Use bullet lists for the "what comes next" items
    - Keep it concise — this is a summary, not a detailed plan

    ## Acceptance criteria
    - `website/docs/roadmap.mdx` exists
    - File has YAML frontmatter with `sidebar_position: 5` and `title: Roadmap`
    - Contains a phase status table showing Phases 0-4 with status (Complete/In Progress)
    - "What comes next" section mentions additional populations, geographic coverage, code/dataset artifacts
    - Phase 4 marked as "In Progress"
    - Phases 0-3 marked as "Complete"

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/roadmap.mdx && grep -q "sidebar_position: 5" website/docs/roadmap.mdx && grep -q "Complete" website/docs/roadmap.mdx && grep -q "In Progress" website/docs/roadmap.mdx && grep -q "additional populations" website/docs/roadmap.mdx && grep -q "geographic" website/docs/roadmap.mdx && echo "Section 5 OK"
    ```

### 8. Create GitHub Actions Deployment Workflow

- **Task ID**: github-actions-deploy
- **Role**: builder
- **Depends On**: scaffold-docusaurus
- **Assigned To**: builder-1
- **Description**: |
    Create a GitHub Actions workflow that builds the Docusaurus site and deploys it to GitHub Pages. The workflow should trigger on pushes to `main` that touch files under `website/`.

    ## What to do

    1. Create the directory `.github/workflows/` at the repo root:
       ```bash
       mkdir -p /Users/anvith/aegis/.github/workflows
       ```

    2. Create `.github/workflows/deploy-docs.yml` with the following content:
       ```yaml
       name: Deploy Docs to GitHub Pages

       on:
         push:
           branches:
             - main
           paths:
             - 'website/**'
         workflow_dispatch:

       permissions:
         contents: read
         pages: write
         id-token: write

       concurrency:
         group: "pages"
         cancel-in-progress: false

       jobs:
         build:
           runs-on: ubuntu-latest
           defaults:
             run:
               working-directory: website
           steps:
             - name: Checkout
               uses: actions/checkout@v4

             - name: Setup Node.js
               uses: actions/setup-node@v4
               with:
                 node-version: '20'
                 cache: npm
                 cache-dependency-path: website/package-lock.json

             - name: Install dependencies
               run: npm ci

             - name: Build site
               run: npm run build

             - name: Upload artifact
               uses: actions/upload-pages-artifact@v3
               with:
                 path: website/build

         deploy:
           environment:
             name: github-pages
             url: ${{ steps.deployment.outputs.page_url }}
           runs-on: ubuntu-latest
           needs: build
           steps:
             - name: Deploy to GitHub Pages
               id: deployment
               uses: actions/deploy-pages@v4
       ```

    ## Files to create
    - `.github/workflows/deploy-docs.yml`

    ## Files to modify
    - None

    ## Code patterns to follow
    - Use `actions/checkout@v4`, `actions/setup-node@v4`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4`
    - Use `workflow_dispatch` for manual triggering
    - Set `working-directory: website` on the build job
    - Use `npm ci` (not `npm install`) for CI builds
    - Trigger on `website/**` path changes only

    ## Acceptance criteria
    - `.github/workflows/deploy-docs.yml` exists
    - Workflow triggers on push to main with `website/**` path filter
    - Workflow also supports `workflow_dispatch`
    - Build job: checks out code, sets up Node 20, installs deps with `npm ci`, runs `npm run build`
    - Deploy job: deploys to GitHub Pages
    - Permissions include `pages: write` and `id-token: write`

    ## Validation command
    ```bash
    cd /Users/anvith/aegis && test -f .github/workflows/deploy-docs.yml && grep -q "deploy-pages" .github/workflows/deploy-docs.yml && grep -q "npm ci" .github/workflows/deploy-docs.yml && grep -q "npm run build" .github/workflows/deploy-docs.yml && grep -q "website/\\*\\*" .github/workflows/deploy-docs.yml && grep -q "workflow_dispatch" .github/workflows/deploy-docs.yml && echo "GitHub Actions OK"
    ```

### 9. Build Validation

- **Task ID**: build-validation
- **Role**: builder
- **Depends On**: content-what-is-aegis, content-how-it-works, content-architecture, content-data-sources, content-roadmap, placeholder-images, github-actions-deploy
- **Assigned To**: builder-1
- **Description**: |
    Run the Docusaurus production build to verify everything compiles correctly. Fix any build errors.

    ## What to do

    1. Navigate to the website directory and run the production build:
       ```bash
       cd /Users/anvith/aegis/website && npm run build
       ```

    2. If the build fails, read the error output carefully and fix the issues. Common issues:
       - Broken links: check that all internal links in MDX files point to existing pages
       - Missing frontmatter: every MDX file needs YAML frontmatter with at least `title`
       - Invalid MDX syntax: JSX expressions in MDX must be valid
       - Missing image files: ensure placeholder images exist at `website/static/images/`
       - Sidebar references: ensure every doc ID in `sidebars.ts` has a matching file in `website/docs/`

    3. If the build succeeds, verify the output directory exists:
       ```bash
       ls -la /Users/anvith/aegis/website/build/
       ```

    4. Verify that all expected pages were generated by checking for HTML files:
       ```bash
       find /Users/anvith/aegis/website/build/docs -name "*.html" | sort
       ```
       Expected output should include pages for all 10 content pages:
       - what-is-aegis
       - how-it-works/data-pipeline
       - how-it-works/identity-resolution
       - how-it-works/integrity-gate
       - how-it-works/scoring
       - how-it-works/feedback-loop
       - architecture/overview
       - architecture/diagrams
       - data-sources
       - roadmap

    ## Files to modify
    - Any files that cause build errors (fix in place)

    ## Acceptance criteria
    - `npm run build` completes with exit code 0
    - `website/build/` directory exists with generated HTML
    - All 10 content pages have corresponding HTML output
    - No broken link errors

    ## Validation command
    ```bash
    cd /Users/anvith/aegis/website && npm run build 2>&1 && test -d build && echo "Build OK"
    ```

### 10. Final Validation

- **Task ID**: validate-all
- **Role**: validator
- **Depends On**: build-validation
- **Assigned To**: validator
- **Description**: |
    Run all validation commands and verify all acceptance criteria for the complete Docusaurus documentation site.

    ## Validation Commands

    1. Verify Docusaurus scaffold:
    ```bash
    cd /Users/anvith/aegis/website && test -f package.json && test -f docusaurus.config.ts && test -f sidebars.ts && test -f tsconfig.json && test -f src/pages/index.tsx && test -f src/css/custom.css && test -d node_modules && echo "Scaffold OK"
    ```

    2. Verify all content pages exist:
    ```bash
    cd /Users/anvith/aegis && test -f website/docs/what-is-aegis.mdx && test -f website/docs/how-it-works/data-pipeline.mdx && test -f website/docs/how-it-works/identity-resolution.mdx && test -f website/docs/how-it-works/integrity-gate.mdx && test -f website/docs/how-it-works/scoring.mdx && test -f website/docs/how-it-works/feedback-loop.mdx && test -f website/docs/architecture/overview.mdx && test -f website/docs/architecture/diagrams.mdx && test -f website/docs/data-sources.mdx && test -f website/docs/roadmap.mdx && echo "All 10 content pages exist"
    ```

    3. Verify placeholder images:
    ```bash
    cd /Users/anvith/aegis && (test -f website/static/images/architecture.png || test -f website/static/images/architecture.svg) && (test -f website/static/images/data-flow.png || test -f website/static/images/data-flow.svg) && echo "Placeholder images OK"
    ```

    4. Verify GitHub Actions workflow:
    ```bash
    cd /Users/anvith/aegis && test -f .github/workflows/deploy-docs.yml && grep -q "deploy-pages" .github/workflows/deploy-docs.yml && grep -q "npm ci" .github/workflows/deploy-docs.yml && grep -q "workflow_dispatch" .github/workflows/deploy-docs.yml && echo "GitHub Actions OK"
    ```

    5. Verify .gitignore updates:
    ```bash
    cd /Users/anvith/aegis && grep -q "website/node_modules" .gitignore && grep -q "website/.docusaurus" .gitignore && grep -q "website/build" .gitignore && echo "Gitignore OK"
    ```

    6. Verify sidebar structure in sidebars.ts:
    ```bash
    cd /Users/anvith/aegis && grep -q "what-is-aegis" website/sidebars.ts && grep -q "how-it-works" website/sidebars.ts && grep -q "architecture" website/sidebars.ts && grep -q "data-sources" website/sidebars.ts && grep -q "roadmap" website/sidebars.ts && echo "Sidebar OK"
    ```

    7. Verify content quality — key terms present:
    ```bash
    cd /Users/anvith/aegis && grep -q "Recency" website/docs/what-is-aegis.mdx && grep -q "Translational" website/docs/what-is-aegis.mdx && grep -q "Drug Discovery" website/docs/what-is-aegis.mdx && grep -q "Clinician" website/docs/what-is-aegis.mdx && grep -q "Event-driven" website/docs/how-it-works/data-pipeline.mdx && grep -q "ORCID" website/docs/how-it-works/identity-resolution.mdx && grep -q "Retraction Watch" website/docs/how-it-works/integrity-gate.mdx && grep -q "MeSH" website/docs/how-it-works/scoring.mdx && grep -q "Fleiss" website/docs/how-it-works/feedback-loop.mdx && grep -q "Phase 0" website/docs/architecture/overview.mdx && grep -q "PubMed" website/docs/data-sources.mdx && grep -q "In Progress" website/docs/roadmap.mdx && echo "Content quality OK"
    ```

    8. Run production build:
    ```bash
    cd /Users/anvith/aegis/website && npm run build 2>&1 && test -d build && echo "Build OK"
    ```

    9. Verify all HTML pages generated:
    ```bash
    cd /Users/anvith/aegis/website && find build/docs -name "*.html" 2>/dev/null | wc -l | xargs test 8 -le && echo "HTML pages generated OK"
    ```

    ## Acceptance Criteria

    - Docusaurus 3.x project scaffolded at `website/` with package.json, config, sidebar, homepage
    - All 10 MDX content pages exist across 5 sections
    - Section 1 (What is Aegis): scoring formula in plain English (R, Q, C, I), three populations explained
    - Section 2 (How It Works): 5 pages covering data pipeline, identity resolution, integrity gate, scoring, feedback loop
    - Section 3 (Architecture): phase-by-phase overview (Phases 0-4), placeholder diagrams referenced
    - Section 4 (Data Sources): ~25 sources in categorized tables with cadence and populations
    - Section 5 (Roadmap): phase status table, what comes next
    - Placeholder images exist (architecture and data-flow)
    - GitHub Actions workflow at `.github/workflows/deploy-docs.yml` for GitHub Pages deployment
    - `.gitignore` updated for website build artifacts
    - `npm run build` succeeds with zero errors
    - Sidebar navigation matches the 5 sections with correct ordering

## Acceptance Criteria

- Docusaurus 3.x project exists at `website/` with valid `package.json`, `docusaurus.config.ts`, `sidebars.ts`, and `tsconfig.json`
- Custom homepage at `website/src/pages/index.tsx` with hero section and feature cards
- Sidebar configuration in `sidebars.ts` defines 5 sections: What is Aegis, How It Works (category with 5 pages), System Architecture (category with 2 pages), Data Sources, Roadmap
- 10 MDX content pages total:
  - `website/docs/what-is-aegis.mdx` — scoring formula in plain English, three populations
  - `website/docs/how-it-works/data-pipeline.mdx` — ~25 sources, three cadence tiers
  - `website/docs/how-it-works/identity-resolution.mdx` — ORCID, NPI, ROR, probabilistic linking
  - `website/docs/how-it-works/integrity-gate.mdx` — hard disqualifiers, soft signals, contestability
  - `website/docs/how-it-works/scoring.mdx` — R, Q, C components with sub-scores, weight learning
  - `website/docs/how-it-works/feedback-loop.mdx` — Fleiss kappa, accept rate, weekly relearning
  - `website/docs/architecture/overview.mdx` — Phases 0-4 with built/unlocked structure
  - `website/docs/architecture/diagrams.mdx` — placeholder image references
  - `website/docs/data-sources.mdx` — ~25 sources in categorized tables
  - `website/docs/roadmap.mdx` — phase status table, what comes next
- Placeholder images at `website/static/images/architecture.png` (or `.svg`) and `website/static/images/data-flow.png` (or `.svg`)
- GitHub Actions workflow at `.github/workflows/deploy-docs.yml` with GitHub Pages deployment, triggered on `website/**` changes
- `.gitignore` includes `website/node_modules/`, `website/.docusaurus/`, `website/build/`
- `npm run build` completes successfully with zero errors
- No API reference, no module-level docs, no versioning — high-level documentation only

## Validation Commands

Execute these commands to validate the task is complete:

- `cd /Users/anvith/aegis/website && test -f package.json && test -f docusaurus.config.ts && test -f sidebars.ts && echo "Scaffold exists"` — Verify Docusaurus scaffold
- `cd /Users/anvith/aegis && ls website/docs/what-is-aegis.mdx website/docs/how-it-works/data-pipeline.mdx website/docs/how-it-works/identity-resolution.mdx website/docs/how-it-works/integrity-gate.mdx website/docs/how-it-works/scoring.mdx website/docs/how-it-works/feedback-loop.mdx website/docs/architecture/overview.mdx website/docs/architecture/diagrams.mdx website/docs/data-sources.mdx website/docs/roadmap.mdx` — Verify all 10 content pages exist
- `cd /Users/anvith/aegis && (test -f website/static/images/architecture.png || test -f website/static/images/architecture.svg) && echo "Architecture image OK"` — Verify placeholder architecture image
- `cd /Users/anvith/aegis && test -f .github/workflows/deploy-docs.yml && echo "GH Actions OK"` — Verify GitHub Actions workflow
- `cd /Users/anvith/aegis && grep -q "website/node_modules" .gitignore && echo "Gitignore OK"` — Verify .gitignore update
- `cd /Users/anvith/aegis/website && npm run build 2>&1 && echo "Build OK"` — Verify production build succeeds

## Notes

- Docusaurus 3.x requires Node.js >= 18. The GitHub Actions workflow uses Node 20.
- The site URL is configured as `https://anvithv.github.io/aegis/` for GitHub Pages deployment from the `AnvithV/aegis` repo.
- Placeholder images are intentionally simple. Actual architecture and data-flow diagrams should be created separately using Excalidraw or Figma and dropped in as replacements.
- The `website/` directory is fully self-contained within the aegis repo — it has its own `package.json`, `node_modules/`, and build pipeline separate from the Python backend.
- The `frontend/` directory (Phase 4a Next.js app) already exists in the repo. The `website/` directory is separate and serves a different purpose (documentation vs. application).
- No new Python dependencies are needed. This is entirely a Node.js/TypeScript project within the `website/` subdirectory.
- Run `cd /Users/anvith/aegis/website && npm install` to install dependencies before attempting a build.
