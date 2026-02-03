
import { useState } from "react";

/* ─────────────────────────── DONNÉES ─────────────────────────── */
const ELEMENTS = {
  panneaux: {
    label: "Panneaux Solaires",
    icon: "☀️",
    desc: "Captent l'énergie solaire et la convertissent en courant électrique continu (DC). C'est la première source d'énergie dans la chaîne de priorité.",
    role: "Source primaire d'énergie renouvelable.",
  },
  onduleur: {
    label: "Onduleur / Inverter",
    icon: "🔄",
    desc: "Convertit le courant continu (DC) produit par les panneaux solaires en courant alternatif (AC) utilisable par les appareils électriques. Dans un système hybride, il peut aussi charger les batteries et gérer les flux d'énergie.",
    role: "Convertisseur DC→AC et gestionnaire des flux solaires.",
  },
  batteries: {
    label: "Batteries",
    icon: "🔋",
    desc: "Stockent l'énergie solaire excédentaire sous forme de courant continu. Elles fournissent de l'énergie la nuit ou quand le soleil est insuffisant. La capacité de stockage détermine l'autonomie du système.",
    role: "Stockage de l'énergie solaire pour usage différé.",
  },
  stabilisateur: {
    label: "Stabilisateur",
    icon: "⚖️",
    desc: "Placé en amont du tableau compteur JIRAMA, il stabilise la tension du réseau public. Les variations de tension (surtensions, sous-tensions) peuvent endommager le matériel — le stabilisateur les atténue.",
    role: "Protection et régulation de la tension réseau.",
  },
  tableauCompteur: {
    label: "Tableau du Compteur",
    icon: "📋",
    desc: "Point central de réception de l'énergie JIRAMA après stabilisation. C'est le nœud de distribution vers le local technique et les ATS. Tous les départs sont protégés par des disjoncteurs.",
    role: "Nœud de distribution principal du réseau public.",
  },
  ats1: {
    label: "ATS1",
    icon: "🔀",
    desc: "Automatic Transfer Switch n°1. Il sélectionne automatiquement entre l'énergie SOLAIRE et l'énergie JIRAMA. Si le solaire est disponible (priorité), il le choisit. Sinon, il bascule vers JIRAMA.",
    role: "Sélection automatique : Solaire ↔ JIRAMA.",
  },
  atsSdmo: {
    label: "ATS SDMO",
    icon: "🔀",
    desc: "Automatic Transfer Switch principal (associé au groupe électrogène SDMO). Il fait la sélection finale entre le réseau (sortie ATS1) et le groupe électrogène. C'est le dernier point de décision avant la distribution.",
    role: "Sélection finale : Réseau (ATS1) ↔ Groupe Électrogène.",
  },
  geSDMO: {
    label: "Groupe Électrogène SDMO",
    icon: "🔥",
    desc: "Source de secours en dernier recours. Il génère du courant AC en fonctionnant au diesel. Il ne démarre que si ni le solaire, ni le JIRAMA ne sont disponibles (via l'ATS SDMO).",
    role: "Secours ultime en cas de panne des autres sources.",
  },
  disjoncteurs: {
    label: "Disjoncteurs",
    icon: "🔐",
    desc: "Dispositifs de protection automatiques. Ils coupent le courant en cas de surcharge ou de court-circuit pour éviter les incendies ou les dégâts matériels. Les disjoncteurs différentiels protègent aussi contre les fuites de courant.",
    role: "Protection des circuits contre surcharges et courts-circuits.",
  },
};

const DIAGNOSTIC_CASES = [
  {
    titre: "☀️ Panne Solaire",
    symptome: "Le système ne détecte plus d'énergie solaire",
    points: [
      { etape: "1", action: "Vérifier l'exposition des panneaux (ombre, saleté, neige)" },
      { etape: "2", action: "Contrôler les voyants de l'onduleur solaire (erreur, alarme)" },
      { etape: "3", action: "Vérifier les câbles entre panneaux et onduleur (loose, corrosion)" },
      { etape: "4", action: "Mesurer la tension de sortie des panneaux avec un multimètre" },
      { etape: "5", action: "Vérifier le niveau de charge des batteries" },
    ],
    causes: ["Panneaux encrassés ou en ombre", "Câble de liaison endommagé", "Onduleur en panne", "Batteries en fin de vie"],
    corrections: ["Nettoyer les panneaux", "Remplacer le câble défaillant", "Redémarrer l'onduleur ou le remplacer", "Vérifier l'état de santé des batteries"],
  },
  {
    titre: "⚡ Coupure JIRAMA",
    symptome: "Le réseau public est coupé",
    points: [
      { etape: "1", action: "Confirmer la coupure (vérifier le compteur JIRAMA)" },
      { etape: "2", action: "Vérifier si l'ATS1 bascule vers le solaire" },
      { etape: "3", action: "Si pas de solaire, vérifier si l'ATS SDMO démarre le GE" },
      { etape: "4", action: "Contrôler les voyants sur les deux ATS" },
      { etape: "5", action: "Vérifier le stabilisateur (pas de sortie en cas de coupure totale)" },
    ],
    causes: ["Coupure réseau JIRAMA", "ATS1 non fonctionnel", "Solaire insuffisant et GE non démarré"],
    corrections: ["Attendre le retour du réseau", "Vérifier la programmation de l'ATS1", "Démarrer manuellement le GE si possible"],
  },
  {
    titre: "🔥 GE qui ne démarre pas",
    symptome: "Le groupe électrogène SDMO ne met pas en route",
    points: [
      { etape: "1", action: "Vérifier le niveau de carburant (diesel)" },
      { etape: "2", action: "Contrôler la batterie de démarrage du GE" },
      { etape: "3", action: "Vérifier le signal de démarrage envoyé par l'ATS SDMO" },
      { etape: "4", action: "Inspecter les filtres à carburant et à huile" },
      { etape: "5", action: "Vérifier la led/voyant d'état sur le tableau de bord du GE" },
    ],
    causes: ["Manque de carburant", "Batterie de démarrage faible", "Problème mécanique (filtres, injecteurs)", "Signal ATS non reçu"],
    corrections: ["Ravitailler en diesel", "Charger ou remplacer la batterie de démarrage", "Nettover/remplacer les filtres", "Vérifier le câblage entre ATS SDMO et GE"],
  },
  {
    titre: "🔀 Basculement ATS défaillant",
    symptome: "L'ATS ne bascule pas correctement entre les sources",
    points: [
      { etape: "1", action: "Identifier quel ATS est concerné (ATS1 ou ATS SDMO)" },
      { etape: "2", action: "Vérifier les voyants d'état de l'ATS concerné" },
      { etape: "3", action: "Contrôler les tensions en entrée et en sortie avec un multimètre" },
      { etape: "4", action: "Vérifier la programmation du délai de basculement" },
      { etape: "5", action: "Tester le basculement manuellement si le mode manuel est disponible" },
    ],
    causes: ["ATS en panne mécanique ou électronique", "Programmation incorrecte", "Tension en entrée hors seuil", "Câblage défaillant"],
    corrections: ["Redémarrer l'ATS", "Reconfigurer les paramètres de démarrage", "Vérifier et remettre en conf les câbles", "Appeler le technicien si panne persistante"],
  },
  {
    titre: "🔌 Prises sans courant, lumières OK",
    symptome: "Les lumières fonctionnent mais les prises ne donnent pas de courant",
    points: [
      { etape: "1", action: "Vérifier le disjoncteur différentiel du circuit prises" },
      { etape: "2", action: "Contrôler l'onduleur en sortie vers les prises (voyant, alarme)" },
      { etape: "3", action: "Vérifier si l'onduleur est en surcharge ou en alarme" },
      { etape: "4", action: "Tester une prise avec un appareil de faible puissance" },
      { etape: "5", action: "Vérifier les disjoncteurs divisionnaires du circuit prises" },
    ],
    causes: ["Disjoncteur différentiel déclenché", "Onduleur en panne ou surcharge", "Court-circuit sur une prise", "Câble de liaison coupé"],
    corrections: ["Relever le disjoncteur différentiel", "Débrancher les appareils lourds puis relancer l'onduleur", "Identifier et isoler la prise défaillante", "Vérifier et remplacer le câble"],
  },
  {
    titre: "⚠️ Surcharge onduleur",
    symptome: "L'onduleur signale une surcharge (alarme, voyant rouge)",
    points: [
      { etape: "1", action: "Vérifier la puissance totale connectée sur les prises" },
      { etape: "2", action: "Identifier les appareils à forte consommation (climatiseur, four, etc.)" },
      { etape: "3", action: "Vérifier le voyant d'alarme sur l'onduleur" },
      { etape: "4", action: "Contrôler la tension de sortie de l'onduleur" },
      { etape: "5", action: "Vérifier le niveau de charge des batteries" },
    ],
    causes: ["Trop d'appareils branchés simultanément", "Appareil à forte puissance dépasse la capacité", "Batteries faibles limitant la sortie", "Onduleur sous-dimensionné"],
    corrections: ["Débrancher les appareils non essentiels", "Utiliser les appareils lourds un par un", "Charger les batteries", "Évaluer l'ajout d'un onduleur plus puissant"],
  },
];

/* ─────────────────────── SVG SCHÉMA ─────────────────────── */
function SchemasSVG({ activeSource }) {
  const highlight = (src) => activeSource === "all" || activeSource === src;
  const pathStyle = (src, extra = {}) => ({
    stroke: highlight(src) ? (src === "solaire" ? "#34d399" : src === "jirama" ? "#60a5fa" : "#fb923c") : "#334155",
    strokeWidth: highlight(src) ? 3 : 1.5,
    fill: "none",
    opacity: highlight(src) ? 1 : 0.35,
    transition: "all 0.4s",
    ...extra,
  });
  const boxStyle = (src, extra = {}) => ({
    fill: highlight(src)
      ? src === "solaire" ? "#064e3b" : src === "jirama" ? "#1e3a5f" : "#431407"
      : "#1e293b",
    stroke: highlight(src)
      ? src === "solaire" ? "#34d399" : src === "jirama" ? "#60a5fa" : "#fb923c"
      : "#475569",
    strokeWidth: highlight(src) ? 2 : 1,
    opacity: highlight(src) ? 1 : 0.5,
    transition: "all 0.4s",
    ...extra,
  });

  return (
    <svg viewBox="0 0 900 580" style={{ width: "100%", maxWidth: 900, background: "#0f172a", borderRadius: 12, border: "1px solid #1e293b" }}>
      <defs>
        <marker id="arrowGreen"  markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#34d399"/></marker>
        <marker id="arrowBlue"   markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#60a5fa"/></marker>
        <marker id="arrowOrange" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#fb923c"/></marker>
        <marker id="arrowWhite"  markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#94a3b8"/></marker>
        <marker id="arrowYellow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#facc15"/></marker>
        <marker id="arrowCyan"   markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="#38bdf8"/></marker>
      </defs>

      {/* ─────── TITRE ─────── */}
      <text x="450" y="24" textAnchor="middle" fill="#94a3b8" fontSize="13" fontFamily="'SF Mono', monospace" fontWeight="600">SCHÉMA FONCTIONNEL — INSTALLATION HYBRIDE</text>

      {/* ═══════════════════════════════════════════
          LIGNE 1  —  SOURCES  (y 42-88)
          Solaire gauche | JIRAMA centre | GE droite
      ═══════════════════════════════════════════ */}

      {/* ── Panneaux Solaires ── */}
      <rect x="18" y="42" width="128" height="46" rx="8" style={boxStyle("solaire")}/>
      <text x="82" y="61" textAnchor="middle" fill="#34d399" fontSize="11" fontWeight="700" fontFamily="sans-serif">☀️ Panneaux</text>
      <text x="82" y="77" textAnchor="middle" fill="#a7f3d0" fontSize="9" fontFamily="sans-serif">Solaires</text>

      {/* ── Onduleur Solaire ── */}
      <rect x="182" y="42" width="128" height="46" rx="8" style={boxStyle("solaire")}/>
      <text x="246" y="61" textAnchor="middle" fill="#34d399" fontSize="11" fontWeight="700" fontFamily="sans-serif">🔄 Onduleur</text>
      <text x="246" y="77" textAnchor="middle" fill="#a7f3d0" fontSize="9" fontFamily="sans-serif">Solaire</text>

      {/* Panneaux → Onduleur */}
      <line x1="146" y1="65" x2="180" y2="65" style={pathStyle("solaire")} markerEnd="url(#arrowGreen)"/>

      {/* ── Batteries (sous l'onduleur) ── */}
      <rect x="182" y="114" width="128" height="36" rx="8" style={boxStyle("solaire")}/>
      <text x="246" y="128" textAnchor="middle" fill="#34d399" fontSize="10.5" fontWeight="700" fontFamily="sans-serif">🔋 Batteries</text>
      <text x="246" y="143" textAnchor="middle" fill="#a7f3d0" fontSize="9" fontFamily="sans-serif">Stockage</text>
      {/* Onduleur ↔ Batteries */}
      <line x1="246" y1="88" x2="246" y2="112" style={pathStyle("solaire")} markerEnd="url(#arrowGreen)"/>

      {/* ── JIRAMA ── */}
      <rect x="370" y="42" width="128" height="46" rx="8" style={boxStyle("jirama")}/>
      <text x="434" y="61" textAnchor="middle" fill="#60a5fa" fontSize="11" fontWeight="700" fontFamily="sans-serif">⚡ JIRAMA</text>
      <text x="434" y="77" textAnchor="middle" fill="#bfdbfe" fontSize="9" fontFamily="sans-serif">Réseau Public</text>

      {/* ── Stabilisateur ── */}
      <rect x="370" y="114" width="128" height="36" rx="8" style={boxStyle("jirama")}/>
      <text x="434" y="128" textAnchor="middle" fill="#60a5fa" fontSize="10.5" fontWeight="700" fontFamily="sans-serif">⚖️ Stabilisateur</text>
      <text x="434" y="143" textAnchor="middle" fill="#bfdbfe" fontSize="9" fontFamily="sans-serif">Régulation</text>
      {/* JIRAMA → Stabilisateur */}
      <line x1="434" y1="88" x2="434" y2="112" style={pathStyle("jirama")} markerEnd="url(#arrowBlue)"/>

      {/* ── Tableau Compteur ── */}
      <rect x="370" y="180" width="128" height="36" rx="8" style={boxStyle("jirama")}/>
      <text x="434" y="194" textAnchor="middle" fill="#60a5fa" fontSize="10.5" fontWeight="700" fontFamily="sans-serif">📋 Tableau Compteur</text>
      <text x="434" y="209" textAnchor="middle" fill="#bfdbfe" fontSize="9" fontFamily="sans-serif">Nœud principal</text>
      {/* Stabilisateur → Tableau */}
      <line x1="434" y1="150" x2="434" y2="178" style={pathStyle("jirama")} markerEnd="url(#arrowBlue)"/>

      {/* ── GE SDMO ── */}
      <rect x="590" y="42" width="128" height="46" rx="8" style={boxStyle("ge")}/>
      <text x="654" y="61" textAnchor="middle" fill="#fb923c" fontSize="11" fontWeight="700" fontFamily="sans-serif">🔥 GE SDMO</text>
      <text x="654" y="77" textAnchor="middle" fill="#fdba74" fontSize="9" fontFamily="sans-serif">Groupe Élec.</text>

      {/* ═══════════════════════════════════════════
          LIGNE 2  —  ATS1  (y 258-316)
          Entrées :  Onduleur Solaire (gauche)
                   + Tableau Compteur (droite)
      ═══════════════════════════════════════════ */}

      {/* ── ATS1 ── */}
      <rect x="298" y="258" width="184" height="56" rx="12" style={{ fill: "#1e1b4b", stroke: "#a78bfa", strokeWidth: 2.5 }}/>
      <text x="390" y="282" textAnchor="middle" fill="#a78bfa" fontSize="15" fontWeight="800" fontFamily="sans-serif">ATS1</text>
      <text x="390" y="303" textAnchor="middle" fill="#c4b5fd" fontSize="9.5" fontFamily="sans-serif">Solaire ↔ JIRAMA</text>

      {/* Onduleur → ATS1 (gauche) : descend puis entre à gauche */}
      <line x1="246" y1="88" x2="246" y2="240" style={pathStyle("solaire")}/>
      <line x1="246" y1="240" x2="296" y2="284" style={pathStyle("solaire")} markerEnd="url(#arrowGreen)"/>
      <text x="228" y="234" textAnchor="end" fill="#34d399" fontSize="8" fontFamily="'SF Mono', monospace" opacity="0.85">sortie onduleur</text>

      {/* Tableau Compteur → ATS1 (droite) : descend puis entre à droite */}
      <line x1="498" y1="198" x2="498" y2="240" style={pathStyle("jirama")}/>
      <line x1="498" y1="240" x2="484" y2="284" style={pathStyle("jirama")} markerEnd="url(#arrowBlue)"/>
      <text x="516" y="234" textAnchor="start" fill="#60a5fa" fontSize="8" fontFamily="'SF Mono', monospace" opacity="0.85">vers ATS1</text>

      {/* ═══════════════════════════════════════════
          LIGNE 3  —  Sortie ATS1 → retour Tableau Compteur → ATS SDMO
      ═══════════════════════════════════════════ */}

      {/* ATS1 sortie vers le bas */}
      <line x1="390" y1="314" x2="390" y2="350" style={{ stroke: "#94a3b8", strokeWidth: 2.5, fill: "none" }} markerEnd="url(#arrowWhite)"/>

      {/* Petit nœud "retour tableau compteur" */}
      <rect x="298" y="352" width="184" height="28" rx="8" fill="#1e293b" stroke="#475569" strokeWidth="1.5"/>
      <text x="390" y="371" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="'SF Mono', monospace" fontWeight="600">↩ Retour Tableau Compteur</text>

      {/* Descend vers ATS SDMO */}
      <line x1="390" y1="380" x2="390" y2="412" style={{ stroke: "#94a3b8", strokeWidth: 2.5, fill: "none" }} markerEnd="url(#arrowWhite)"/>

      {/* ═══════════════════════════════════════════
          LIGNE 4  —  ATS SDMO  (y 414-474)
          Entrées :  Réseau (retour tableau, haut)
                   + GE SDMO           (droite)
      ═══════════════════════════════════════════ */}

      {/* ── ATS SDMO ── */}
      <rect x="274" y="414" width="232" height="58" rx="12" style={{ fill: "#292524", stroke: "#fb923c", strokeWidth: 2.5 }}/>
      <text x="390" y="440" textAnchor="middle" fill="#fb923c" fontSize="15" fontWeight="800" fontFamily="sans-serif">ATS SDMO</text>
      <text x="390" y="462" textAnchor="middle" fill="#fdba74" fontSize="9.5" fontFamily="sans-serif">Sélection finale : Réseau ↔ GE</text>

      {/* GE SDMO ──► ATS SDMO : ligne verticale puis horizontale depuis droite */}
      <line x1="654" y1="88" x2="654" y2="443" style={pathStyle("ge")}/>
      <line x1="654" y1="443" x2="508" y2="443" style={pathStyle("ge")} markerEnd="url(#arrowOrange)"/>

      {/* ═══════════════════════════════════════════
          LIGNE 5  —  DISTRIBUTION  (y 492+)
      ═══════════════════════════════════════════ */}

      {/* ATS SDMO → barre */}
      <line x1="390" y1="472" x2="390" y2="498" style={{ stroke: "#fb923c", strokeWidth: 3, fill: "none" }} markerEnd="url(#arrowOrange)"/>

      {/* Barre de distribution */}
      <rect x="130" y="500" width="520" height="18" rx="6" fill="#1e293b" stroke="#475569" strokeWidth="1.5"/>
      <text x="390" y="513" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="'SF Mono', monospace" fontWeight="600">BARRE DE DISTRIBUTION</text>

      {/* ── Circuit Éclairage ── */}
      <line x1="260" y1="518" x2="260" y2="534" style={{ stroke: "#facc15", strokeWidth: 2, fill: "none" }} markerEnd="url(#arrowYellow)"/>
      <rect x="170" y="536" width="180" height="24" rx="7" fill="#1a1a0e" stroke="#facc15" strokeWidth="1.5"/>
      <text x="260" y="553" textAnchor="middle" fill="#facc15" fontSize="10.5" fontWeight="700" fontFamily="sans-serif">💡 ÉCLAIRAGE</text>
      <text x="260" y="576" textAnchor="middle" fill="#86efac" fontSize="8.5" fontFamily="sans-serif">Disj. différentiel → Disj. divisionnaires → Lumières</text>

      {/* ── Circuit Prises ── */}
      <line x1="520" y1="518" x2="520" y2="534" style={{ stroke: "#38bdf8", strokeWidth: 2, fill: "none" }} markerEnd="url(#arrowCyan)"/>
      <rect x="430" y="536" width="180" height="24" rx="7" fill="#0c1a2e" stroke="#38bdf8" strokeWidth="1.5"/>
      <text x="520" y="553" textAnchor="middle" fill="#38bdf8" fontSize="10.5" fontWeight="700" fontFamily="sans-serif">🔌 PRISES</text>
      <text x="520" y="576" textAnchor="middle" fill="#86efac" fontSize="8.5" fontFamily="sans-serif">Onduleur → Disj. diff. → Divisionnaires → Prises</text>

      {/* ═══ LÉGENDE ═══ */}
      <rect x="18" y="258" width="222" height="102" rx="8" fill="#0f172a" stroke="#1e293b" strokeWidth="1"/>
      <text x="129" y="277" textAnchor="middle" fill="#94a3b8" fontSize="9.5" fontFamily="'SF Mono', monospace" fontWeight="600">LÉGENDE</text>
      <line x1="30" y1="291" x2="58" y2="291" stroke="#34d399" strokeWidth="3"/><text x="64" y="295" fill="#a7f3d0" fontSize="9" fontFamily="sans-serif">Solaire (priorité 1)</text>
      <line x1="30" y1="311" x2="58" y2="311" stroke="#60a5fa" strokeWidth="3"/><text x="64" y="315" fill="#bfdbfe" fontSize="9" fontFamily="sans-serif">JIRAMA (priorité 2)</text>
      <line x1="30" y1="331" x2="58" y2="331" stroke="#fb923c" strokeWidth="3"/><text x="64" y="335" fill="#fdba74" fontSize="9" fontFamily="sans-serif">GE SDMO (priorité 3)</text>
      <line x1="30" y1="349" x2="58" y2="349" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5,3"/><text x="64" y="353" fill="#94a3b8" fontSize="9" fontFamily="sans-serif">Liaison neutre</text>
    </svg>
  );
}

/* ─────────────────────── COMPOSANT PRINCIPAL ─────────────────────── */
export default function App() {
  const [tab, setTab] = useState("schema");
  const [selectedElement, setSelectedElement] = useState(null);
  const [diagnosIndex, setDiagnosIndex] = useState(null);
  const [activeSource, setActiveSource] = useState("all");

  const tabs = [
    { id: "schema", label: "📐 Schéma" },
    { id: "elements", label: "🧩 Éléments" },
    { id: "fonctionnement", label: "📖 Fonctionnement" },
    { id: "diagnostic", label: "🛠️ Diagnostic" },
  ];

  return (
    <div style={{ background: "#0f172a", minHeight: "100vh", color: "#e2e8f0", fontFamily: "'Segoe UI', sans-serif", padding: "0 12px 40px" }}>
      {/* HEADER */}
      <div style={{ background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", borderBottom: "1px solid #1e293b", padding: "18px 16px 12px", textAlign: "center" }}>
        <h1 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: "-0.5px", color: "#f1f5f9" }}>
          ⚡ Installation Électrique Hybride
        </h1>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#64748b" }}>
          Guide technique — Solaire · JIRAMA · Groupe Électrogène
        </p>
      </div>

      {/* TABS */}
      <div style={{ display: "flex", gap: 6, padding: "12px 0", overflowX: "auto", justifyContent: "center" }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: tab === t.id ? "#6366f1" : "#1e293b",
              border: tab === t.id ? "none" : "1px solid #334155",
              color: tab === t.id ? "#fff" : "#94a3b8",
              padding: "8px 14px",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
              whiteSpace: "nowrap",
              transition: "all 0.2s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ═══════════════ TAB : SCHEMA ═══════════════ */}
      {tab === "schema" && (
        <div>
          {/* Filtres source */}
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginBottom: 10, flexWrap: "wrap" }}>
            {[
              { id: "all", label: "Tout", color: "#94a3b8" },
              { id: "solaire", label: "☀️ Solaire", color: "#34d399" },
              { id: "jirama", label: "⚡ JIRAMA", color: "#60a5fa" },
              { id: "ge", label: "🔥 GE", color: "#fb923c" },
            ].map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSource(s.id)}
                style={{
                  background: activeSource === s.id ? s.color + "22" : "transparent",
                  border: `1.5px solid ${activeSource === s.id ? s.color : "#334155"}`,
                  color: activeSource === s.id ? s.color : "#64748b",
                  padding: "4px 12px",
                  borderRadius: 20,
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: 600,
                  transition: "all 0.2s",
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
          <SchemasSVG activeSource={activeSource} />
          <p style={{ textAlign: "center", fontSize: 10.5, color: "#475569", marginTop: 10 }}>
            Utilisez les filtres ci-dessus pour mettre en valeur chaque source d'énergie sur le schéma.
          </p>
        </div>
      )}

      {/* ═══════════════ TAB : ELEMENTS ═══════════════ */}
      {tab === "elements" && (
        <div style={{ maxWidth: 680, margin: "0 auto" }}>
          <p style={{ fontSize: 12, color: "#64748b", textAlign: "center", marginBottom: 12 }}>
            Tapez sur un élément pour voir son rôle détaillé.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {Object.entries(ELEMENTS).map(([key, el]) => (
              <button
                key={key}
                onClick={() => setSelectedElement(selectedElement === key ? null : key)}
                style={{
                  background: selectedElement === key ? "#1e1b4b" : "#1e293b",
                  border: `1.5px solid ${selectedElement === key ? "#a78bfa" : "#334155"}`,
                  borderRadius: 10,
                  padding: "12px 8px",
                  cursor: "pointer",
                  color: "#e2e8f0",
                  textAlign: "center",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ fontSize: 22 }}>{el.icon}</div>
                <div style={{ fontSize: 10.5, fontWeight: 700, marginTop: 4, color: selectedElement === key ? "#c4b5fd" : "#cbd5e1" }}>{el.label}</div>
              </button>
            ))}
          </div>
          {selectedElement && (
            <div style={{ background: "#1e1b4b", border: "1px solid #4c1d95", borderRadius: 12, padding: 18, marginTop: 14, animation: "fadeIn 0.25s" }}>
              <h3 style={{ margin: "0 0 6px", color: "#a78bfa", fontSize: 15 }}>
                {ELEMENTS[selectedElement].icon} {ELEMENTS[selectedElement].label}
              </h3>
              <p style={{ margin: "0 0 10px", fontSize: 13, color: "#c4b5fd", fontWeight: 600 }}>
                Rôle : {ELEMENTS[selectedElement].role}
              </p>
              <p style={{ margin: 0, fontSize: 12.5, color: "#ddd8fe", lineHeight: 1.6 }}>
                {ELEMENTS[selectedElement].desc}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════ TAB : FONCTIONNEMENT ═══════════════ */}
      {tab === "fonctionnement" && (
        <div style={{ maxWidth: 680, margin: "0 auto" }}>
          {/* Priorité banner */}
          <div style={{ background: "#1e1b4b", border: "1px solid #4c1d95", borderRadius: 10, padding: "12px 16px", marginBottom: 16, display: "flex", gap: 8, alignItems: "center", justifyContent: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#a78bfa", fontWeight: 700 }}>PRIORITÉ :</span>
            <span style={{ background: "#064e3b", color: "#34d399", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 700 }}>1. Solaire</span>
            <span style={{ color: "#64748b", fontSize: 14 }}>›</span>
            <span style={{ background: "#1e3a5f", color: "#60a5fa", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 700 }}>2. JIRAMA</span>
            <span style={{ color: "#64748b", fontSize: 14 }}>›</span>
            <span style={{ background: "#431407", color: "#fb923c", padding: "3px 10px", borderRadius: 12, fontSize: 11, fontWeight: 700 }}>3. GE SDMO</span>
          </div>

          {/* Étapes */}
          {[
            { num: 1, titre: "Génération Solaire", color: "#34d399", bg: "#064e3b", texte: "Les panneaux solaires captent la lumière solaire et la convertissent en courant continu (DC). Cet énergie est envoyée à l'onduleur solaire." },
            { num: 2, titre: "Conversion & Stockage", color: "#34d399", bg: "#064e3b", texte: "L'onduleur convertit le DC en courant alternatif (AC). Une partie de l'énergie est stockée dans les batteries pour une utilisation ultérieure (nuit, nuageux)." },
            { num: 3, titre: "Sélection par ATS1", color: "#a78bfa", bg: "#1e1b4b", texte: "L'ATS1 vérifie si l'énergie solaire est disponible et suffisante. Si oui → il la sélectionne. Si non → il bascule vers JIRAMA (réseau public via le stabilisateur)." },
            { num: 4, titre: "Sélection Finale — ATS SDMO", color: "#fb923c", bg: "#292524", texte: "L'ATS SDMO reçoit la sortie de l'ATS1. Si cette source est active → elle est utilisée. Si elle tombe → l'ATS SDMO démarre automatiquement le groupe électrogène SDMO." },
            { num: 5, titre: "Distribution", color: "#facc15", bg: "#1c1917", texte: "Le courant sort de l'ATS SDMO et se répartit en deux circuits : l'éclairage (via disjoncteurs différentiel + divisionnaires) et les prises (via un onduleur puis des disjoncteurs)." },
          ].map((step) => (
            <div key={step.num} style={{ display: "flex", gap: 12, marginBottom: 14, alignItems: "flex-start" }}>
              <div style={{ minWidth: 36, height: 36, borderRadius: "50%", background: step.bg, border: `2px solid ${step.color}`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, color: step.color, fontSize: 14 }}>
                {step.num}
              </div>
              <div style={{ background: "#1e293b", borderRadius: 10, padding: "10px 14px", flex: 1, border: "1px solid #334155" }}>
                <div style={{ color: step.color, fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{step.titre}</div>
                <div style={{ color: "#cbd5e1", fontSize: 12.5, lineHeight: 1.6 }}>{step.texte}</div>
              </div>
            </div>
          ))}

          {/* Résumé */}
          <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 10, padding: 16, marginTop: 20 }}>
            <h4 style={{ margin: "0 0 8px", color: "#f1f5f9", fontSize: 14 }}>📝 Résumé simplifié</h4>
            <p style={{ margin: 0, fontSize: 12.5, color: "#cbd5e1", lineHeight: 1.7 }}>
              Le système essaie d'utiliser <strong style={{ color: "#34d399" }}>le solaire en premier</strong>. S'il n'y a pas assez, il passe au <strong style={{ color: "#60a5fa" }}>réseau JIRAMA</strong>. Si le réseau tombe aussi, le <strong style={{ color: "#fb923c" }}>groupe électrogène SDMO</strong> démarre automatiquement. Tout ce basculement est géré par deux ATS en cascade (ATS1 puis ATS SDMO). L'énergie final se distribue ensuite vers les lumières et les prises via des disjoncteurs de protection.
            </p>
          </div>
        </div>
      )}

      {/* ═══════════════ TAB : DIAGNOSTIC ═══════════════ */}
      {tab === "diagnostic" && (
        <div style={{ maxWidth: 700, margin: "0 auto" }}>
          <p style={{ fontSize: 12, color: "#64748b", textAlign: "center", marginBottom: 10 }}>Sélectionnez un type de panne pour voir le protocole de diagnostic.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8, marginBottom: 16 }}>
            {DIAGNOSTIC_CASES.map((c, i) => (
              <button
                key={i}
                onClick={() => setDiagnosIndex(diagnosIndex === i ? null : i)}
                style={{
                  background: diagnosIndex === i ? "#1e1b4b" : "#1e293b",
                  border: `1.5px solid ${diagnosIndex === i ? "#a78bfa" : "#334155"}`,
                  borderRadius: 10,
                  padding: "10px 10px",
                  cursor: "pointer",
                  color: diagnosIndex === i ? "#c4b5fd" : "#cbd5e1",
                  textAlign: "left",
                  fontSize: 12,
                  fontWeight: 600,
                  transition: "all 0.2s",
                }}
              >
                {c.titre}
              </button>
            ))}
          </div>

          {diagnosIndex !== null && (
            <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, overflow: "hidden", animation: "fadeIn 0.3s" }}>
              {/* Header */}
              <div style={{ background: "#1e1b4b", padding: "12px 16px", borderBottom: "1px solid #334155" }}>
                <h3 style={{ margin: 0, color: "#c4b5fd", fontSize: 15 }}>{DIAGNOSTIC_CASES[diagnosIndex].titre}</h3>
                <p style={{ margin: "4px 0 0", fontSize: 11.5, color: "#a78bfa" }}>
                  🔍 Symptôme : {DIAGNOSTIC_CASES[diagnosIndex].symptome}
                </p>
              </div>

              <div style={{ padding: 16 }}>
                {/* Points de contrôle */}
                <h4 style={{ margin: "0 0 8px", color: "#f1f5f9", fontSize: 13 }}>📋 Points de contrôle (ordre logique)</h4>
                {DIAGNOSTIC_CASES[diagnosIndex].points.map((p, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 8 }}>
                    <div style={{ minWidth: 24, height: 24, borderRadius: "50%", background: "#312e81", border: "1.5px solid #6366f1", display: "flex", alignItems: "center", justifyContent: "center", color: "#a5b4fc", fontSize: 11, fontWeight: 700 }}>
                      {p.etape}
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "#cbd5e1", paddingTop: 3, lineHeight: 1.5 }}>{p.action}</p>
                  </div>
                ))}

                {/* Causes */}
                <h4 style={{ margin: "16px 0 8px", color: "#fb923c", fontSize: 13 }}>⚠️ Causes probables</h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {DIAGNOSTIC_CASES[diagnosIndex].causes.map((c, i) => (
                    <span key={i} style={{ background: "#292524", border: "1px solid #44403c", borderRadius: 6, padding: "3px 10px", fontSize: 11, color: "#fdba74" }}>{c}</span>
                  ))}
                </div>

                {/* Actions correctives */}
                <h4 style={{ margin: "16px 0 8px", color: "#34d399", fontSize: 13 }}>✅ Actions correctives</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  {DIAGNOSTIC_CASES[diagnosIndex].corrections.map((c, i) => (
                    <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <span style={{ color: "#34d399", fontSize: 13 }}>→</span>
                      <span style={{ fontSize: 12, color: "#a7f3d0" }}>{c}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STYLE ANIMATION */}
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        button:hover { filter: brightness(1.1); }
        ::-webkit-scrollbar { height: 4px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }
      `}</style>
    </div>
  );
}
