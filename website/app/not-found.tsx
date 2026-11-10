import Link from "next/link";

export default function NotFound() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">That page doesn&apos;t exist.</h1>
        <div className="actions"><Link className="btn main" href="/">Go home</Link></div>
      </header>
    </div>
  );
}
