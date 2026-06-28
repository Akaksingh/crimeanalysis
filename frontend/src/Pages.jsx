import React, { useState } from 'react';

// ===========================================================
// Content pages reproduced from the official Karnataka State
// Police portal (https://ksp.karnataka.gov.in). Text is taken
// verbatim from the corresponding pages so this mirrors the
// real site; only the surrounding chrome is our project's.
// ===========================================================

function PageHead({ title, kn, lead }) {
  return (
    <div className="page-head">
      <h2>{title}</h2>
      {kn && <div className="page-head-kn" lang="kn">{kn}</div>}
      {lead && <p className="page-lead">{lead}</p>}
    </div>
  );
}

// sub-menu within a section (mirrors the site's dropdown items)
function SubTabs({ tabs, active, onChange }) {
  return (
    <div className="subnav">
      {tabs.map((t) => (
        <button key={t.id} className={active === t.id ? 'on' : ''} onClick={() => onChange(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------- About Us
const ABOUT_TABS = [
  { id: 'vision', label: 'Vision Statement' },
  { id: 'history', label: 'History' },
  { id: 'organization', label: 'Organization' },
  { id: 'org-structure', label: 'Organizational Structure' },
];

export function AboutPage() {
  const [tab, setTab] = useState('vision');
  return (
    <div className="page">
      <PageHead title="About Us" kn="ನಮ್ಮ ಬಗ್ಗೆ" />
      <SubTabs tabs={ABOUT_TABS} active={tab} onChange={setTab} />
      {tab === 'vision' && <Vision />}
      {tab === 'history' && <History />}
      {tab === 'organization' && <Organization />}
      {tab === 'org-structure' && <OrgStructure />}
    </div>
  );
}

// Textual rendering of the KSP organizational chart (top-down hierarchy).
const ORG_LADDER = [
  { rank: 'Director General & Inspector General of Police (DG&IGP)', note: 'Head of the Karnataka State Police; reports to the State Government.' },
  { rank: 'Additional Director General of Police (ADGP)', note: 'Heads major wings — Law & Order, Administration, Crime, Intelligence, Recruitment, etc.' },
  { rank: 'Inspector General of Police (IGP)', note: 'Commands a Police Range or a specialised wing.' },
  { rank: 'Deputy Inspector General of Police (DIGP)', note: 'Assists the IGP in supervising a range / division.' },
  { rank: 'Superintendent of Police (SP) / Deputy Commissioner of Police (DCP)', note: 'District Police chief (SP) or city sub-division head (DCP).' },
  { rank: 'Additional SP / Assistant Commissioner of Police (ACP)', note: 'Supervises a sub-division.' },
  { rank: 'Deputy Superintendent of Police (DySP)', note: 'Sub-divisional Police Officer.' },
  { rank: 'Police Inspector (PI)', note: 'Station House Officer in charge of a Police Station / Circle.' },
  { rank: 'Police Sub-Inspector (PSI) / Assistant Sub-Inspector (ASI)', note: 'Investigating and station-level officers.' },
  { rank: 'Head Constable & Police Constable', note: 'Front-line policing, patrolling and beat duties.' },
];

function OrgStructure() {
  return (
    <>
      <section className="panel">
        <h3>Organizational Structure</h3>
        <p>
          Karnataka State Police follows a hierarchical command structure headed by
          the <b>Director General &amp; Inspector General of Police (DG&amp;IGP)</b>.
          The state is divided into <b>Police Ranges</b>, each comprising several
          <b> districts</b>; districts are further divided into <b>sub-divisions</b>,
          <b> circles</b> and <b>police stations</b>. City policing is organised under
          <b> Commissionerates</b>. The chain of command from the state headquarters
          down to the police station is as follows:
        </p>
      </section>

      <section className="panel">
        <h3>Chain of Command (top to bottom)</h3>
        <ol className="numbered">
          {ORG_LADDER.map((r) => (
            <li key={r.rank}><b>{r.rank}</b> — {r.note}</li>
          ))}
        </ol>
      </section>

      <section className="panel">
        <h3>Field &amp; Territorial Hierarchy</h3>
        <p className="org-flow">
          State Headquarters (DG&amp;IGP) → Police Range (IGP/DIGP) → District /
          City Commissionerate (SP / Commissioner) → Sub-division (DySP / ACP) →
          Circle (Police Inspector) → Police Station (PI / PSI) → Beats &amp; Patrols
          (Head Constables &amp; Constables).
        </p>
      </section>
    </>
  );
}

function Vision() {
  return (
    <section className="panel">
      <h3>Vision Statement</h3>
      <blockquote className="quote">
        “Karnataka State Police shall uphold the Law and the Rights of all people
        for a safe and secure environment, conducive to their internal and
        external growth and development.”
      </blockquote>
      <p>Towards this end, the organization sets the following objectives:</p>
      <ul className="bullet">
        <li>Protect the lives and liberties of the people from criminal and anti-social elements.</li>
        <li>Earn the goodwill, support and active assistance of the community.</li>
        <li>Co-ordinate with other departments of Criminal Justice System.</li>
        <li>Equal treatment regardless of caste, religion, social and economic status or political affiliations.</li>
        <li>Due consideration for women, children, senior citizens and weaker sections.</li>
        <li>Improve professional knowledge, skills and attitudes and adopt modern methods in police work.</li>
        <li>Promote human rights and professional values of integrity, honesty and efficiency.</li>
        <li>Accept and play our role in social transformation and bring about improvement in the quality of life with society.</li>
      </ul>
    </section>
  );
}

function History() {
  return (
    <section className="panel article">
      <h3>History of Karnataka State Police</h3>

      <h4>Preface</h4>
      <p>
        Police in Karnataka were called by various names in different regions.
        After initiation of Policing, they were initially called Thoti, Talwar,
        Umbalidhar, Kattubidi, Neeraganti etc. The police primarily with policing
        used to do other jobs entrusted to them. The foundation of present police
        set up was laid after the appointment of State's first Inspector General
        of Police. Today the State Police has grown into a big and complex
        organization running on modern management principles.
      </p>

      <h4>History</h4>
      <p>
        Mysore State was the predecessor to Karnataka State. Sri. L. Rickets was
        appointed as first Inspector General of Police, prior to which the State
        Police had no status, structure and powers as such. During 1883 it was
        reported that Talwars, Thotis, Neeragantis, Kavalugararu, Amaragararu,
        Ankamaale, Patela, Shyanubhogas etc. used to do policing. During the rule
        of Maharajas of Mysore, the policing existed in different variants.
      </p>

      <h4>Judicial System</h4>
      <p>
        In the year 1856, when the Judicial System became functional, Judicial
        Commissioners were appointed. In 1873 a rank of Deputy Inspector General
        of Police was appointed to assist him. During the same period posts of
        first class Inspector, second class Inspectors, Jamadhars, Daphedhars
        (Head Constables) and Constables were created. At Taluk levels Amaldhars
        continued as police chiefs.
      </p>

      <h4>First IGP</h4>
      <p>
        Reformation of police system took place in the year 1883. On the 1st of
        November 1885 Sri Ricket was appointed the First Inspector General of
        Police of old Mysore State. Later Sri V.P. Madhav Rao took over the charge
        from Sri Rickets. A separate policing was enforced for cities of Mysore
        and Bangalore. Under the guidance of the Inspector General of Police, the
        Head Quarter Inspector Sri. N. Laxman Shasthri published a guided hand
        book for police.
      </p>

      <h4>Independence Movement</h4>
      <p>
        From 1939 onwards the winds of freedom struggle blew strongly in the Royal
        State of Mysore. The heat of Civil disobedience had hit the police force.
        Leaders Sri. H. Siddaiah, T. Subramanyam, Malavalli Veerappa along with
        2000 protesters were arrested.
      </p>

      <h4>After 1956</h4>
      <p>
        In 1956 the reorganization of states was done in India on linguistic
        basis. On the same lines the Mysore state came into existence in 1956. The
        unified state police got a uniform dress code under Mysore Police. Sri P.K.
        Monappa was the first Inspector General of Police and also State's first IP
        (Imperial Police) Officer. As Karnataka was unified from various regions,
        the Karnataka Police Act 1963 came into force from 2nd April 1965,
        enforcing a uniform Police regulation across the entire state.
      </p>

      <h4>Bangalore City</h4>
      <p>
        After unification of Karnataka, Bangalore as Capital City grew very
        rapidly, posing various challenges to the police. Bangalore City became a
        Commissionerate on 4th July 1963. Sri. C. Chandhy, a Senior Deputy
        Inspector General of Police, was appointed as the Police Commissioner.
      </p>

      <h4>Armed Reserve Police</h4>
      <p>
        To contain and control law and order situations like protests and rallies,
        Karnataka Reserve Police was created. In 1956 the state had three
        battalions; presently it has eleven Battalions along with two India Reserve
        Battalions, with four Battalions at Head Quarters in Bangalore and the rest
        located at Mysore, Belgaum, Gulbarga, Mangalore, Shimoga, Hassan and
        Shiggao in Haveri District.
      </p>

      <h4>Women Police</h4>
      <p>
        With the aim of social reforms, the department started recruiting Women
        Police. Smt. Jija Hari Singh was the first woman IPS officer in the State
        of Karnataka and Smt. Prabharao IPS was the first Kannadiga woman IPS. At
        present 36 women police stations are functioning in Karnataka.
      </p>

      <h4>Police Dog Squad</h4>
      <p>
        Police Dogs were utilized from 1968. Initially the squad had six canines
        which have now increased to more than 38 Dog Squads and 234 dogs, with a
        Dog Training school situated at CAR South, Bengaluru City.
      </p>
    </section>
  );
}

const RANGES = [
  { name: 'Southern Range (Mysuru)', area: 'Mysuru, Kodagu, Mandya, Hassan, Chamarajanagara' },
  { name: 'Western Range (Mangalore)', area: 'Dakshina Kannada, Uttara Kannada, Udupi, Chikkamagaluru' },
  { name: 'Eastern Range (Davangere)', area: 'Chitradurga, Haveri, Shivamogga, Davangere' },
  { name: 'Central Range (Bengaluru)', area: 'Tumakuru, Kolar, Bengaluru Rural, KGF, Chikkaballapura, Ramanagara' },
  { name: 'Northern Range (Belagavi)', area: 'Belagavi, Vijayapura, Dharwad, Bagalkote, Gadag' },
  { name: 'North Eastern Range (Kalaburagi)', area: 'Kalaburagi, Bidar, Yadagiri' },
  { name: 'Ballari Range', area: 'Ballari, Vijayanagara, Raichur, Koppala' },
];

function Organization() {
  return (
    <>
      <section className="panel">
        <h3>Organization</h3>
        <p>
          The Director General and Inspector General of Police leads the
          department, supported by Additional Director Generals and Inspector
          Generals. There are <b>6 Police Commissionerates</b> in Karnataka; the
          Bengaluru City Police Commissioner is of the rank of Additional Director
          General of Police.
        </p>
      </section>

      <section className="panel">
        <h3>Police Ranges</h3>
        <p>The state operates seven ranges, each headed by an Inspector General, overseeing 3–6 districts per range:</p>
        <div className="unit-grid">
          {RANGES.map((r) => (
            <div className="unit-card" key={r.name}>
              <div className="unit-name">{r.name}</div>
              <div className="unit-desc">{r.area}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h3>Major Departments</h3>
        <ul className="bullet">
          <li>Crime &amp; Technical Services</li>
          <li>Criminal Investigation Department (CID)</li>
          <li>Karnataka State Reserve Police (12 battalions)</li>
          <li>Internal Security Division — counter-terrorism and organized crime</li>
        </ul>
      </section>
    </>
  );
}

// ---------------------------------------------------------- Crime (KSP portal mirror)
const CRIME_TABS = [
  { id: 'fir', label: 'FIR Cases' },
  { id: 'udr', label: 'UDR Cases' },
  { id: 'petty', label: 'Petty Cases' },
  { id: 'crimes', label: 'Crimes' },
  { id: 'cyber', label: 'Cyber Crime' },
];

export function CrimePage() {
  const [tab, setTab] = useState('fir');
  return (
    <div className="page">
      <PageHead
        title="Crime"
        kn="ಅಪರಾಧ"
        lead="Case categories handled by Karnataka State Police under the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023."
      />
      <SubTabs tabs={CRIME_TABS} active={tab} onChange={setTab} />
      {tab === 'fir' && <FIRCases />}
      {tab === 'udr' && <UDRCases />}
      {tab === 'petty' && <PettyCases />}
      {tab === 'crimes' && <Crimes />}
      {tab === 'cyber' && <CyberCrime />}
    </div>
  );
}

function FIRCases() {
  return (
    <section className="panel article">
      <h3>FIR Cases</h3>
      <h4>What is an FIR?</h4>
      <p>
        An FIR (First Information Report) is the earliest form and the first
        information of a <b>cognizable offence</b> recorded by an officer-in-charge
        of a police station under Section 173 of the Bharatiya Nagarik Suraksha
        Sanhita, 2023 (BNSS).
      </p>
      <h4>Who Can File an FIR</h4>
      <p>Filing an FIR is not restricted to victims alone. Any person with knowledge of a cognizable offence may submit one — including a police officer who discovers such an offence. Eligible filers include a person who:</p>
      <ul className="bullet">
        <li>is the person against whom the offence was committed;</li>
        <li>has personal knowledge of an offence; or</li>
        <li>witnessed the offence being committed.</li>
      </ul>
      <h4>Filing Procedure</h4>
      <p>
        When information about a cognizable offence is given orally, the police must
        record it in writing. The recorded information is read back to the person
        filing, who signs it after verifying its accuracy. A person unable to read or
        write may provide a left thumb impression. The complainant has the right to
        receive a <b>copy of the FIR free of cost</b> under Section 173(2) of BNSS, 2023.
      </p>
      <h4>Required Information</h4>
      <p>
        An FIR should include your name and address, the date, time and location of
        the incident, the factual details, descriptions of the persons involved, and
        details of any witnesses.
      </p>
    </section>
  );
}

function UDRCases() {
  return (
    <section className="panel article">
      <h3>UDR Cases</h3>
      <h4>What is a UDR?</h4>
      <p>UDR stands for <b>Unnatural Death Report</b>.</p>
      <h4>Definition of Unnatural Death</h4>
      <p>An unnatural death occurs when a person dies through circumstances such as:</p>
      <ul className="bullet">
        <li>Accidents — drowning, snake bite, electric contact, natural calamities;</li>
        <li>Suicide — hanging, self-immolation, jumping into water;</li>
        <li>being killed by another person, or by an animal or machinery; or</li>
        <li>death under suspicious circumstances.</li>
      </ul>
      <h4>Legal Framework</h4>
      <p>
        Under Section 194 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS),
        when the police receive information about such a death they must:
      </p>
      <ol className="numbered">
        <li>immediately notify the nearest Executive Magistrate;</li>
        <li>investigate and document the apparent cause of death;</li>
        <li>the investigating officer signs the report and forwards it to the District or Sub-divisional Magistrate within 24 hours.</li>
      </ol>
      <p>The resulting document is the Unnatural Death Report (UDR).</p>
    </section>
  );
}

function PettyCases() {
  return (
    <section className="panel article">
      <h3>Petty Cases</h3>
      <h4>What Are Petty Cases?</h4>
      <p>
        A <b>"petty offence"</b> means any offence punishable only with a fine not
        exceeding five thousand rupees, as defined in Section 2(1)(m) of the
        Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS).
      </p>
      <h4>Key Characteristics</h4>
      <ul className="bullet">
        <li><b>Fine threshold:</b> the maximum penalty is ₹5,000 (increased from ₹1,000 under the previous law).</li>
        <li><b>Exclusions:</b> traffic violations under the Motor Vehicles Act, 1988, and cases permitting conviction without the accused's presence are not classified as petty offences.</li>
      </ul>
      <h4>Procedural Features</h4>
      <ul className="bullet">
        <li>Special summons allowing defendants to respond by mail or through a representative;</li>
        <li>Summary trials (mandatory for petty cases);</li>
        <li>Conviction on a guilty plea even when the accused is absent;</li>
        <li>Limited appeal rights in most circumstances.</li>
      </ul>
      <h4>Purpose</h4>
      <p>
        The framework aims to deliver faster justice while reducing court backlogs by
        enabling efficient handling of minor infractions without lengthy proceedings.
      </p>
    </section>
  );
}

const OFFENCE_TYPES = [
  { t: 'Cognizable Offences', d: 'Serious crimes such as murder and rape, for which the police can arrest without a warrant and begin investigation without court permission.' },
  { t: 'Non-Cognizable Offences', d: 'Less serious offences that require the permission of a court before the police can investigate.' },
  { t: 'Bailable Offences', d: 'Offences for which the accused has a right to bail upon providing a bond.' },
  { t: 'Non-Bailable Offences', d: 'More serious offences where the grant of bail is at the discretion of the court.' },
];

function Crimes() {
  return (
    <section className="panel">
      <h3>Crimes</h3>
      <p>
        Offences are classified under the Bharatiya Nagarik Suraksha Sanhita (BNSS),
        2023. The principal classifications are:
      </p>
      <div className="unit-grid">
        {OFFENCE_TYPES.map((o) => (
          <div className="unit-card" key={o.t}>
            <div className="unit-name">{o.t}</div>
            <div className="unit-desc">{o.d}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

const CYBER_TYPES = [
  { t: 'Phishing & Social Engineering', d: 'Deceptive emails, SMS or fake websites designed to steal credentials, OTPs and personal data, often impersonating trusted institutions.' },
  { t: 'Investment & Money Multiplication Scams', d: 'False promises of guaranteed returns via social media or messaging apps, requiring initial deposits that subsequently vanish.' },
  { t: 'Romance & Catfishing Scams', d: 'Fabricated emotional connections built online to extract money, frequently targeting isolated individuals or seniors.' },
  { t: 'Fake Tech Support', d: 'Pop-ups or calls claiming device infection, seeking remote access or demanding payment for bogus repairs.' },
  { t: 'Online Job / Part-time Work Scam', d: 'Fraudulent work-from-home opportunities requiring registration fees or task deposits.' },
  { t: 'Sextortion / Blackmail', d: 'Threats to share intimate or morphed images/videos unless a ransom is paid.' },
  { t: 'Cyberstalking / Cyberbullying / CSAM', d: 'Online harassment targeting women and children, including creation of child sexual abuse material.' },
  { t: 'Malware / Ransomware Attacks', d: 'Malicious software that steals data, corrupts files, or locks devices demanding a cryptocurrency ransom.' },
];

function CyberCrime() {
  return (
    <>
      <section className="panel">
        <h3>Cyber Crime</h3>
        <p>
          Cyber crime is one of the most pressing threats in the digital age, and its
          methods continuously evolve — ranging from financial fraud and identity
          theft to sextortion and ransomware attacks.
        </p>
        <div className="callout callout-pink">
          <div className="callout-num">1930</div>
          <div>
            <b>National Cyber Crime Helpline · 24×7</b>
            <div className="muted small">
              "Digital arrest" does <b>not</b> exist under Indian law. No legitimate
              official will demand money over a phone or video call to avoid arrest.
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Types of Cyber Crime</h3>
        <div className="unit-grid">
          {CYBER_TYPES.map((c) => (
            <div className="unit-card" key={c.t}>
              <div className="unit-name">{c.t}</div>
              <div className="unit-desc">{c.d}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h3>Cyber Hygiene — Safety Tips</h3>
        <ul className="bullet">
          <li>Never share OTPs or credentials.</li>
          <li>Use strong passwords with two-factor authentication.</li>
          <li>Avoid clicking unknown links.</li>
          <li>Verify website legitimacy (https://, official domains).</li>
          <li>Update software regularly.</li>
          <li>Avoid public Wi-Fi for banking.</li>
          <li>Educate children and back up data regularly.</li>
        </ul>
      </section>

      <section className="panel">
        <h3>If You Become a Victim</h3>
        <ol className="numbered">
          <li>Stop transactions immediately and preserve evidence.</li>
          <li>Contact helpline <b>1930</b> (National Cyber Crime Helpline).</li>
          <li>File an online complaint at <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">cybercrime.gov.in</a>.</li>
          <li>Visit the nearest Cyber Crime Police Station.</li>
          <li>Block your bank cards immediately.</li>
          <li>Preserve all communications and screenshots.</li>
        </ol>
      </section>
    </>
  );
}

// ---------------------------------------------------------- Women & Children
const WC_TABS = [
  { id: 'caw', label: 'Crime Against Women' },
  { id: 'safety', label: 'Women Safety' },
  { id: 'child', label: 'Child Abuse' },
];

export function WomenChildrenPage() {
  const [tab, setTab] = useState('caw');
  return (
    <div className="page">
      <PageHead title="Women & Children" kn="ಮಹಿಳೆಯರು ಮತ್ತು ಮಕ್ಕಳು" />
      <div className="callout callout-pink">
        <div className="callout-num">1091</div>
        <div>
          <b>Women Helpline (Vanitha Sahayavani) · 24×7</b>
          <div className="muted small">For any woman in distress — immediate police assistance.</div>
        </div>
        <div className="callout-num">1098</div>
        <div>
          <b>Childline</b>
          <div className="muted small">Emergency helpline for children in need of care and protection.</div>
        </div>
      </div>
      <SubTabs tabs={WC_TABS} active={tab} onChange={setTab} />
      {tab === 'caw' && <CrimeAgainstWomen />}
      {tab === 'safety' && <WomenSafety />}
      {tab === 'child' && <ChildAbuse />}
    </div>
  );
}

const CAW = [
  { t: 'Eve Teasing', d: 'Making unwanted comments, whistling, gestures, or showing obscene things in public to harass a woman. Addressed through Pink Hoysala patrols in public spaces.' },
  { t: 'Sexual Harassment', d: 'Unwanted physical contact, demands for sexual favours, or display of obscene material. Response includes fast FIR processing at women help desks.' },
  { t: 'Rape', d: 'Non-consensual sexual intercourse, including cases involving deception or false promises. Gang rape of minors warrants life imprisonment or the death penalty.' },
  { t: 'Harassment to Married Women', d: 'Physical or mental abuse by spouse or in-laws, including dowry-related torture, often resolved through counselling.' },
  { t: 'Kidnapping', d: 'Unlawful confinement for forced marriage or trafficking, with higher sentences for ransom or severe crimes.' },
  { t: 'Domestic Violence', d: 'Multi-form abuse — physical, sexual, emotional, verbal and economic. Police provide protection orders, counselling and shelter coordination through dedicated women officers.' },
  { t: 'Acid Attacks', d: 'Causing permanent disfigurement through corrosive substances. Treated as heinous crimes with mandatory victim medical cost coverage.' },
];

function CrimeAgainstWomen() {
  return (
    <section className="panel">
      <h3>Crime Against Women</h3>
      <div className="unit-grid">
        {CAW.map((c) => (
          <div className="unit-card" key={c.t}>
            <div className="unit-name">{c.t}</div>
            <div className="unit-desc">{c.d}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function WomenSafety() {
  return (
    <section className="panel">
      <h3>Women Safety Initiatives</h3>
      <ol className="numbered">
        <li>
          <b>Vanitha Sahayavani (Helpline 1091)</b> — established by the Bengaluru
          City Police, the first community-collaboration initiative dedicated to
          the protection and support of women. It operates continuously through the
          toll-free number 1091.
        </li>
        <li>
          <b>Pink Hoysalas</b> — dedicated women-staffed patrol vehicles for
          responding to distress calls involving women and children, providing
          visible police presence and rapid response in public areas.
        </li>
        <li>
          <b>Akka Squad (Akka Pade)</b> — a women-led rapid response initiative
          jointly run by Karnataka Police and the Women &amp; Child Welfare
          Department. Each unit includes women officers, constables, home guards
          and support staff with dedicated transportation, addressing harassment,
          violence, child-related issues, awareness campaigns and prevention in
          public spaces, institutions and online.
        </li>
        <li>
          <b>Women Help Desks</b> — established in police stations throughout the state.
        </li>
      </ol>
      <h4>Emergency Helplines</h4>
      <ul className="bullet">
        <li><b>112</b> — Pan-India emergency (Police, including women safety response)</li>
        <li><b>1091 / 181</b> — Women-specific helplines for distress, violence and support</li>
        <li><b>1930</b> — Cybercrime helpline</li>
      </ul>
    </section>
  );
}

const CHILD = [
  { t: 'Physical Abuse', d: 'Physical abuse of a child is when a parent or caretaker causes any non-accidental physical injury to a child.' },
  { t: 'Sexual Abuse', d: 'Sexual abuse occurs when an adult uses a child for sexual purposes or involves a child in sexual acts.' },
  { t: 'Emotional Abuse', d: 'Occurs when caregivers harm a child’s mental and social development or cause severe emotional harm.' },
  { t: 'Bullying & Cyberbullying', d: 'Repeated, targeted aggressive behaviour using force, threats or embarrassment. Cyberbullying is its digital equivalent — online or on devices through email, chat or text.' },
  { t: 'Child Neglect', d: 'When a parent or caretaker does not give the care, supervision, affection and support needed for a child’s health, safety and well-being — including physical, emotional, medical and educational neglect.' },
];

function ChildAbuse() {
  return (
    <section className="panel">
      <h3>Child Abuse</h3>
      <div className="unit-grid">
        {CHILD.map((c) => (
          <div className="unit-card" key={c.t}>
            <div className="unit-name">{c.t}</div>
            <div className="unit-desc">{c.d}</div>
          </div>
        ))}
      </div>
      <h4>Resources</h4>
      <ul className="bullet">
        <li>National Tracking System for Missing &amp; Vulnerable Children</li>
        <li>ChildLine — 1098</li>
        <li>Community Child and Adolescent Mental Health Service</li>
        <li>Emergency contact — <b>112</b></li>
      </ul>
    </section>
  );
}

// ---------------------------------------------------------- Police Units
const COMMISSIONERATES = [
  'Bengaluru City', 'Mysuru City', 'Mangaluru City', 'Hubballi-Dharwad City',
  'Belagavi City', 'Kalaburagi City',
];
const SPECIAL_UNITS = [
  { name: 'Criminal Investigation Department (CID)', desc: 'Investigation of serious and specialised crimes.' },
  { name: 'Cyber Crime Police', desc: 'Cyber-enabled and financial fraud investigation (helpline 1930).' },
  { name: 'Internal Security Division (ISD)', desc: 'Counter-terrorism and organized crime.' },
  { name: 'Karnataka State Reserve Police (KSRP)', desc: 'Armed reserve force — 12 battalions for law and order duties.' },
  { name: 'Crime & Technical Services', desc: 'Technical and forensic support for investigation.' },
  { name: 'Intelligence Wing', desc: 'Collection and analysis of security intelligence.' },
  { name: 'Traffic & Road Safety', desc: 'Traffic management, enforcement and road safety.' },
  { name: 'Home Guards & Fire Force', desc: 'Emergency services rendering round-the-clock support.' },
];

export function PoliceUnitsPage() {
  return (
    <div className="page">
      <PageHead
        title="Police Units & Special Units"
        kn="ಪೊಲೀಸ್ ಘಟಕಗಳು ಮತ್ತು ವಿಶೇಷ ಘಟಕಗಳು"
        lead="Karnataka State Police operates through 6 city Commissionerates, 7 territorial ranges and a range of specialised wings."
      />

      <section className="panel">
        <h3>Police Commissionerates (6)</h3>
        <div className="chip-grid">
          {COMMISSIONERATES.map((u) => <span className="chip" key={u}>{u}</span>)}
        </div>
      </section>

      <section className="panel">
        <h3>Police Ranges (7)</h3>
        <div className="unit-grid">
          {RANGES.map((r) => (
            <div className="unit-card" key={r.name}>
              <div className="unit-name">{r.name}</div>
              <div className="unit-desc">{r.area}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h3>Special & Specialised Units</h3>
        <div className="unit-grid">
          {SPECIAL_UNITS.map((u) => (
            <div className="unit-card" key={u.name}>
              <div className="unit-name">{u.name}</div>
              <div className="unit-desc">{u.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------- FAQ
const FAQ_TOPICS = [
  { id: 'online', label: 'Online Police Services' },
  { id: 'traffic', label: 'Traffic' },
  { id: 'cyber', label: 'Cybercrime' },
  { id: 'wc', label: 'Women and Children' },
  { id: 'senior', label: 'Senior Citizens' },
  { id: 'nuisance', label: 'Public Nuisance' },
];

const FAQ_DATA = {
  online: [
    { q: 'What is Seva Sindhu?', a: 'Seva Sindhu is the common citizen service portal/facility of the Government of Karnataka to provide government-related services in one platform.' },
    { q: 'How to access Seva Sindhu?', a: 'Seva Sindhu can be accessed online by the public through the Internet or through identified service delivery centers at District/Taluk/Sub-division/Village level.' },
    { q: 'Which police services are provided in Seva Sindhu?', a: '20 Police services are provided, including Police Verification Certificates (domestic servants, institutions, apprenticeships, marriage alliances, government employees, visa purposes), Complaint Registration, Senior Citizen Registration, Locked Home Details, Amplified Sound System License, Amusement License, Permission for Peaceful Assembly and procession, Petition Disposal, NORI Certificate, NOC for petrol pumps/gas agencies/hotels/bars, Missing Report documentation, Temporary License for Cracker Sales, and NOC for petroleum/diesel/naphtha sales and transport.' },
  ],
  traffic: [
    { q: 'What documents should a person carry while driving/riding?', a: 'Driving licence, registration certificate, emission/PUC certificate, insurance certificate, and fitness certificate/permit/tax paid certificate for transport vehicles. Documents may be original or shown via DigiLocker or the mParivahan app.' },
    { q: 'Who is authorised to collect spot fines for traffic violations?', a: 'Any Traffic Officer of and above the rank of Assistant Sub-Inspector of Police is duly authorised to collect spot fines for traffic violations.' },
    { q: 'Can I use a hands-free device for a mobile phone while driving?', a: 'No. Using hands-free accessories like earphones or Bluetooth headsets while driving is prohibited. Mobile phones are only permitted for navigation purposes while operating a vehicle.' },
    { q: "I don't want to pay the spot fine. What is the other option?", a: 'Violators refusing to pay must surrender their original driving licence and receive an acknowledgment. They may then visit the police station within one week to pay and reclaim the licence, pay at court, or abide by court orders.' },
    { q: 'Can police penalise vehicles registered outside Karnataka?', a: 'No. Police cannot penalise vehicles solely based on out-of-state number plates or registration location.' },
    { q: 'Why have I received a violation ticket for a vehicle I have already sold?', a: 'Notices are issued to registered owners per Transport Department records. Buyers should promptly transfer the vehicle registration to their names to avoid receiving notices for subsequent violations.' },
  ],
  cyber: [
    { q: 'What is Cyber Crime?', a: 'Cyber crime is any unlawful activity committed using computers, mobile phones, the internet, or digital networks to steal money or data, commit fraud, harass, threaten, or harm individuals or organizations.' },
    { q: 'What are common types of cyber crime?', a: 'Online financial fraud, digital arrest/impersonation scams, investment/crypto fraud, phishing & vishing, job/part-time scams, sextortion/online blackmail, cyberstalking/cyberbullying/CSAM, and malware/ransomware.' },
    { q: 'What is "Digital Arrest"?', a: '"Digital arrest" is not recognized under Indian law. No legitimate officials will demand money via phone or video call to avoid arrest. If you receive such calls, disconnect immediately and report to 1930.' },
    { q: 'How can you protect yourself from cyber crime?', a: 'Never share OTPs/PINs/CVVs/passwords, use strong passwords with two-factor authentication, avoid unknown links, verify websites, update devices, avoid public Wi-Fi for banking, monitor children’s activities, and back up important data.' },
    { q: 'How do you report cyber crime?', a: 'Report online via the National Cyber Crime Reporting Portal (cybercrime.gov.in), call 1930 (24/7 toll-free), or visit the nearest cyber crime police station.' },
  ],
  wc: [
    { q: 'Whom shall women and children contact during an emergency?', a: 'Women and children can DIAL 112 during emergencies and can seek help from the police.' },
    { q: 'If the police need to question or interrogate me, can they call me to the police station?', a: 'No, women and children cannot be called to the police station for questioning or interrogation unless the person is accused. Women and children are to be interrogated in the presence of a women police officer at their residence.' },
    { q: 'What procedure should police follow if children are involved in a crime?', a: 'If a child is involved in a crime, police have to follow the procedure as per the Juvenile Justice Act.' },
    { q: 'How can women get protection from sexual harassment at the workplace?', a: 'Women can file a complaint at the nearest police station under the "Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act & Rules, 2013".' },
    { q: 'Which act protects children from sexual offences?', a: 'The Protection of Children from Sexual Offences Act 2012 (POCSO) protects children from sexual offences.' },
  ],
  senior: [
    { q: 'Who are Senior Citizens?', a: 'Persons above 60 years of age are considered senior citizens.' },
    { q: 'What to do when our children are not looking after us well?', a: 'Elderly individuals are safeguarded under the Maintenance and Welfare of Parents and Senior Citizens Act 2007. They may petition the local Assistant Commissioner (Revenue) for assistance under this legislation.' },
    { q: "What to do when our relatives are harassing us for property, when we don't have children?", a: 'Individuals experiencing harassment from relatives regarding property matters can contact their nearby police station to obtain protective measures.' },
    { q: 'How do we get protection from police when we are in trouble?', a: 'One can dial 112 or call the local police and seek immediate protection from the police.' },
    { q: 'Is there any special monitoring system by police to protect senior citizens?', a: 'Senior citizens may enrol their information through the Seva Sindhu portal, which transmits details to local police stations. Police will keep a constant watch and provide protection through beat policing.' },
  ],
  nuisance: [
    { q: 'What is a public nuisance?', a: 'Public nuisance is an offence under Section 270 of the Bharatiya Nyaya Sanhita, 2023 (BNS). It encompasses actions that create danger, annoyance, injury or inconvenience affecting public health, safety, morals or welfare. Police can also take preventive measures under Section 152 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS).' },
    { q: 'What should be done if eve-teasing is noticed in the locality?', a: 'Immediately contact 112 or inform the nearest police station.' },
    { q: 'What should be done if a person is smoking in a public place?', a: 'Smoking in public places is prohibited under Section 4 of the Cigarettes and Other Tobacco Products Act (COTPA), 2003. Report this to the local police or authorised enforcement officers.' },
    { q: 'What should be done if drunk persons create nuisance in public places?', a: 'Contact 112 or inform the nearest police station. Such conduct is punishable under Section 85 of the Karnataka Police Act, 1963.' },
    { q: 'What should be done if loud sound systems or late-night parties create disturbance?', a: 'Contact 112 or the local police station. Loudspeaker usage is regulated under the Noise Pollution (Regulation and Control) Rules, 2000. Complaints can also go to the Karnataka State Pollution Control Board (KSPCB).' },
    { q: 'Whom should we contact regarding illegal gambling or betting activities?', a: 'Inform the nearest police station or call 112. Such activities violate the Karnataka Prevention of Gambling Act, 1963 and Section 79 of the Karnataka Police Act, 1963.' },
  ],
};

export function FAQPage() {
  const [topic, setTopic] = useState('online');
  const [open, setOpen] = useState(0);
  const list = FAQ_DATA[topic];
  return (
    <div className="page">
      <PageHead title="Frequently Asked Questions" kn="ಪದೇ ಪದೇ ಕೇಳಲಾಗುವ ಪ್ರಶ್ನೆಗಳು" />
      <SubTabs tabs={FAQ_TOPICS} active={topic} onChange={(t) => { setTopic(t); setOpen(0); }} />
      <section className="panel">
        <div className="faq-list">
          {list.map((f, i) => (
            <div className={`faq-item ${open === i ? 'open' : ''}`} key={i}>
              <button className="faq-q" onClick={() => setOpen(open === i ? -1 : i)}>
                <span>{f.q}</span>
                <span className="faq-toggle">{open === i ? '−' : '+'}</span>
              </button>
              {open === i && <div className="faq-a">{f.a}</div>}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------- Contact Us
export function ContactPage() {
  return (
    <div className="page">
      <PageHead title="Contact Us" kn="ನಮ್ಮನ್ನು ಸಂಪರ್ಕಿಸಿ" />

      <div className="cols">
        <section className="panel">
          <h3>Karnataka State Police Headquarters</h3>
          <address className="addr">
            No. 2, Nrupathunga Road,<br />
            Bangalore – 560 001, Karnataka, India.
          </address>
          <ul className="contact-list">
            <li><b>Phone:</b> 080-22942111, 080-22942777</li>
            <li><b>Fax:</b> 080-22215911</li>
            <li><b>Email:</b> <a href="mailto:police@ksp.gov.in">police@ksp.gov.in</a></li>
            <li><b>Website:</b> <a href="https://ksp.karnataka.gov.in" target="_blank" rel="noreferrer">ksp.karnataka.gov.in</a></li>
          </ul>
        </section>

        <section className="panel">
          <h3>DGP Control Room</h3>
          <ul className="contact-list">
            <li><b>Phone:</b> 22211777, 22942111, 22942777, 22943404</li>
            <li><b>Mobile:</b> 9480800100 · 7483645561 (WhatsApp)</li>
            <li><b>Email:</b> <a href="mailto:crdgcontrol@ksp.gov.in">crdgcontrol@ksp.gov.in</a></li>
            <li><b>Toll Free:</b> 18004250100, 22942336, 22943292, 22943293</li>
          </ul>
        </section>
      </div>

      <div className="cols">
        <section className="panel">
          <h3>Key Department Contacts</h3>
          <ul className="contact-list">
            <li><b>DG &amp; IGP:</b> 080-22211803, 080-22942999 · <a href="mailto:police@ksp.gov.in">police@ksp.gov.in</a></li>
            <li><b>ADGP (Admin):</b> 080-22942101 · <a href="mailto:adgpadmin@ksp.gov.in">adgpadmin@ksp.gov.in</a></li>
            <li><b>ADGP (L&amp;O):</b> 080-22942103 · <a href="mailto:adgplo@ksp.gov.in">adgplo@ksp.gov.in</a></li>
            <li><b>CID:</b> 080-22254789, 22942211 · <a href="mailto:dgpcid@ksp.gov.in">dgpcid@ksp.gov.in</a></li>
            <li><b>ISD:</b> 080-22943816 · <a href="mailto:dgisd@ksp.gov.in">dgisd@ksp.gov.in</a></li>
          </ul>
        </section>

        <section className="panel">
          <h3>Emergency & Helplines</h3>
          <ul className="contact-list">
            <li><b>Emergency (ERSS):</b> 112</li>
            <li><b>Police:</b> 100</li>
            <li><b>Women Helpline:</b> 1091</li>
            <li><b>Childline:</b> 1098</li>
            <li><b>Cyber Crime:</b> 1930</li>
            <li><b>Ambulance:</b> 108</li>
          </ul>
        </section>
      </div>
    </div>
  );
}