import { Drawn } from "./Bits";

function Arrow() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
          <path d="M1 1L9 5L1 9" fill="none" stroke="#000" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </marker>
      </defs>
    </svg>
  );
}

const line = { className: "ln", pathLength: 1 };
const arrow = { ...line, markerEnd: "url(#arrow)" };

export function Boundary() {
  return (
    <figure className="fig">
      <Arrow />
      <Drawn>
        <svg className="dg" viewBox="0 0 1072 350" role="img" aria-label="Public text has names replaced by tags before crossing to the cloud, and names are restored on the device on the way back. Privileged text is answered by a local model and never crosses.">
          <path className="wall" d="M720 34V344" />
          <text className="m r" x="704" y="24">Your device</text><text className="m l" x="736" y="24">The cloud</text>
          <rect className="box" x="1" y="60" width="229" height="56" rx="14" /><text x="115" y="84">Harlow Orchards asked</text><text className="m" x="115" y="102">The lawyer writes</text>
          <path {...arrow} d="M230 88H298" />
          <rect className="box" x="300" y="60" width="210" height="56" rx="14" /><text x="405" y="84">Mask names</text><text className="m" x="405" y="102">Harlow Orchards → [CLIENT_1]</text>
          <path {...arrow} d="M510 88H798" />
          <rect className="solid" x="560" y="76" width="96" height="24" rx="6" /><text className="w mono" x="608" y="93">[CLIENT_1]</text>
          <rect className="box" x="800" y="60" width="271" height="172" rx="18" /><text x="936" y="142">Cloud model</text><text className="m" x="936" y="162">Sees only the tag</text>
          <path {...line} d="M405 116V130M405 162V176" />
          <rect className="ask" x="346" y="130" width="118" height="32" rx="16" /><text className="m" x="405" y="151">Key stays here</text>
          <path {...arrow} d="M800 204H512" />
          <rect className="solid" x="560" y="192" width="96" height="24" rx="6" /><text className="w mono" x="608" y="209">[CLIENT_1]</text>
          <rect className="box" x="300" y="176" width="210" height="56" rx="14" /><text x="405" y="200">Restore names</text><text className="m" x="405" y="218">[CLIENT_1] → Harlow Orchards</text>
          <path {...arrow} d="M300 204H232" />
          <rect className="box" x="1" y="176" width="229" height="56" rx="14" /><text x="115" y="200">Harlow Orchards</text><text className="m" x="115" y="218">The lawyer reads</text>
          <rect className="box" x="1" y="280" width="229" height="56" rx="14" /><text x="115" y="304">Privileged text</text><text className="m" x="115" y="322">Client files, pasted emails</text>
          <path {...arrow} d="M230 308H298" />
          <rect className="solid" x="300" y="280" width="210" height="56" rx="14" /><text className="w" x="405" y="313">A local model answers</text>
          <text className="m l" x="530" y="304">Stays on this side.</text><text className="m l" x="530" y="322">Nothing crosses.</text>
        </svg>
      </Drawn>
      <figcaption>Everything sent to the cloud passes through one masking step. If masking fails, the call doesn&apos;t happen.</figcaption>
    </figure>
  );
}

export function Lifecycle() {
  return (
    <figure className="fig">
      <Arrow />
      <Drawn>
        <svg className="dg narrow" viewBox="0 -10 860 285" role="img" aria-label="A task in testing moves on device after enough good answers, or to the cloud if trials fail. A task in the cloud keeps being checked and can still move on device. A task on device goes back to testing if it starts failing spot checks.">
          <path {...arrow} d="M730 90C730 14 90 14 90 86" /><text className="m" x="410" y="20">Starts failing spot checks: back to testing</text>
          <rect className="ask" x="1" y="90" width="178" height="56" rx="14" /><text x="90" y="123">Testing</text>
          <path {...arrow} d="M180 118H638" /><text className="m" x="410" y="108">Enough good answers in a row</text>
          <rect className="solid" x="640" y="90" width="180" height="56" rx="14" /><text className="w" x="730" y="123">On device</text>
          <path {...arrow} d="M120 146C120 228 220 228 318 228" /><text className="m" x="168" y="258">Trials fail</text>
          <rect className="box" x="320" y="200" width="180" height="56" rx="14" /><text x="410" y="233">Cloud</text>
          <path {...arrow} d="M500 228C620 228 730 228 730 148" /><text className="m" x="640" y="258">Keeps being checked, and can still earn it</text>
        </svg>
      </Drawn>
      <figcaption>The demo moves a task after three good answers to keep it short. A real firm would need far more.</figcaption>
    </figure>
  );
}
