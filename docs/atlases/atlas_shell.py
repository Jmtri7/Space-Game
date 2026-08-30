"""Shared page shell for the per-culture atlases (Common Kit, Sol Federation,
Vherathi Concord, Drossholt Company). Same visual system as Resin & Rivets /
Standard Issue - Instrument Serif / Archivo / IBM Plex Mono, void-black, flat
strokeless specimens - with a per-atlas accent colour.

css(accent_hex, accent_rgb) -> the <style> block
DEFS -> the offscreen <defs> with the grid pattern
"""

GRIDDEF = ('<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
           '<circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.05"/>'
           '</pattern></defs>')
DEFS = f'<svg width="0" height="0" aria-hidden="true" style="position:absolute">{GRIDDEF}</svg>'


def css(accent="#8fb9c8", accent_rgb="143,185,200"):
    a, ar = accent, accent_rgb
    return f"""<style>
:root{{
  --void:#0a0a0e;--panel:#131319;--panel-2:#17171e;--ink:#ece9f4;--ink-2:#a5a2b6;--ink-3:#6d6a7e;
  --line:#292935;--line-2:#35333f;--accent:{a};--accent-rgb:{ar};
  --skin:#e1b491;--skin-hi:#f4d0ab;--skin-lo:#bd8f6a;--body-out:#141219;
  --warn:#f2962a;--maxw:1120px;
}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--void);color:var(--ink);
  font-family:"Archivo","Segoe UI",system-ui,sans-serif;font-size:16px;line-height:1.65;
  -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(1000px 560px at 84% -10%,rgba(var(--accent-rgb),.12),transparent 60%),
    radial-gradient(880px 520px at 6% 106%,rgba(225,180,145,.08),transparent 62%);
  background-repeat:no-repeat;}}
.wrap{{max-width:var(--maxw);margin:0 auto;padding:0 24px}}
::selection{{background:rgba(var(--accent-rgb),.28);color:#fff}}
:focus-visible{{outline:2px solid var(--accent);outline-offset:3px;border-radius:2px}}
.topbar{{position:sticky;top:0;z-index:40;background:#0c0c11;border-bottom:1px solid var(--line)}}
.topbar .wrap{{display:flex;align-items:center;gap:20px;height:56px}}
.mark{{font-family:"Instrument Serif",Georgia,serif;font-size:1.28rem;white-space:nowrap}}
.mark em{{font-style:italic;color:var(--ink-2)}}
.navlinks{{display:flex;gap:16px;margin-left:auto;flex-wrap:wrap;justify-content:flex-end}}
.navlinks a{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.68rem;text-transform:uppercase;
  letter-spacing:.14em;color:var(--ink-3);text-decoration:none;padding:4px 0;border-bottom:1px solid transparent;
  transition:color .15s,border-color .15s}}
.navlinks a:hover,.navlinks a:focus-visible{{color:var(--ink);border-color:var(--line-2)}}
@media (max-width:820px){{.navlinks{{display:none}}}}
.tag-wip{{font-family:"IBM Plex Mono",monospace;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);border:1px solid rgba(var(--accent-rgb),.35);border-radius:2px;padding:3px 7px;white-space:nowrap}}
.hero{{padding:76px 0 40px}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:.7rem;text-transform:uppercase;letter-spacing:.22em;
  color:var(--ink-3);margin:0 0 20px}}
.hero h1{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.9rem,8vw,5.2rem);
  line-height:1;margin:0 0 18px;text-wrap:balance;letter-spacing:-.005em}}
.hero h1 em{{font-style:italic;color:var(--accent)}}
.dek{{font-size:1.14rem;color:var(--ink-2);max-width:64ch;margin:0 0 26px}}
.status{{border:1px solid var(--line);border-left:2px solid var(--accent);background:var(--panel);
  border-radius:3px;padding:14px 18px;max-width:70ch;font-size:.92rem;color:var(--ink-2)}}
.status b{{color:var(--ink);font-weight:600}}
code.f{{font-family:"IBM Plex Mono",monospace;font-size:.84em;color:var(--accent)}}
.legend{{margin:44px 0 8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden}}
.legend div{{background:var(--panel);padding:16px 18px}}
.legend dt{{font-family:"IBM Plex Mono",monospace;font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:6px}}
.legend dd{{margin:0;font-size:.92rem;color:var(--ink-2)}}
.chapter{{padding:88px 0 8px;scroll-margin-top:72px}}
.chapter-kicker{{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 10px}}
.chapter h2{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.1rem,5vw,3.4rem);
  line-height:1.02;margin:0 0 20px;text-wrap:balance}}
.chapter h2 em{{color:var(--accent);font-style:italic}}
.lead{{max-width:66ch;color:var(--ink-2);margin:0 0 12px}}
.lead b{{color:var(--ink);font-weight:600}}
.subhead{{font-family:"IBM Plex Mono",monospace;font-size:.74rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--ink-3);margin:48px 0 18px;padding-bottom:10px;border-bottom:1px solid var(--line)}}
.grid-outfits{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden;margin:8px 0 0}}
.plate{{display:grid;grid-template-columns:300px minmax(0,1fr);gap:34px;padding:26px 0;border-top:1px solid var(--line)}}
.plate:first-of-type{{border-top:none}}
.plate.wide{{grid-template-columns:1fr}}
@media (max-width:760px){{.plate{{grid-template-columns:1fr;gap:20px}}}}
.viewport{{position:relative;border:1px solid var(--line);border-radius:3px;
  background:radial-gradient(circle at 50% 40%,#16161f 0%,#0c0c11 72%,#090a0d 100%);overflow:hidden}}
.viewport.diagram{{aspect-ratio:6/5}}
.viewport.fig{{aspect-ratio:2/3}}
.viewport svg{{position:absolute;inset:0;width:100%;height:100%}}
.viewport .vlabel{{position:absolute;left:10px;bottom:8px;font-family:"IBM Plex Mono",monospace;font-size:.56rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}}
.isnew{{position:absolute;right:0;top:0;font-family:"IBM Plex Mono",monospace;font-size:.54rem;letter-spacing:.12em;
  text-transform:uppercase;padding:4px 8px;background:var(--accent);color:#06171d;font-weight:600;border-bottom-left-radius:3px}}
.plate-body h3{{font-family:"Archivo",sans-serif;font-weight:600;font-size:1.32rem;margin:2px 0 3px;letter-spacing:-.01em}}
.mk{{color:var(--accent);font-family:"IBM Plex Mono",monospace;font-size:.58em;letter-spacing:.12em}}
.role{{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);opacity:.85;margin:0 0 14px}}
.plate-body p{{margin:0 0 14px;font-size:.95rem;color:var(--ink-2);max-width:60ch}}
.plate-body p b{{color:var(--ink);font-weight:600}}
.spec{{margin:16px 0 0;padding:14px 16px;border:1px solid var(--line);border-radius:3px;background:var(--panel);
  display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-family:"IBM Plex Mono",monospace;font-size:.73rem}}
.spec dt{{color:var(--ink-3)}}
.spec dd{{margin:0;color:var(--ink)}}
.spec .full{{grid-column:1/-1;color:var(--ink-2);padding-top:8px;margin-top:4px;border-top:1px solid var(--line)}}
.keys{{margin:14px 0 0;display:flex;flex-wrap:wrap;gap:6px}}
.keys span{{font-family:"IBM Plex Mono",monospace;font-size:.63rem;padding:3px 7px;border:1px solid var(--line-2);
  border-radius:2px;color:var(--ink-2)}}
.keys span b{{color:var(--ink);font-weight:500}}
.card{{background:var(--panel);margin:0;padding:14px 10px 12px;text-align:center;position:relative}}
.card svg{{width:112px;height:168px;display:block;margin:0 auto}}
.card figcaption{{margin-top:8px}}
.card b{{display:block;font-size:.95rem;color:var(--ink);font-weight:600}}
.card .role{{margin:2px 0 0;font-size:.58rem;letter-spacing:.08em}}
.card .keyline{{margin-top:6px;font-family:"IBM Plex Mono",monospace;font-size:.56rem;color:var(--ink-3);letter-spacing:.02em}}
.identity{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:34px;margin:8px 0 20px;align-items:start}}
@media (max-width:820px){{.identity{{grid-template-columns:1fr;gap:24px}}}}
.swatches{{display:flex;flex-wrap:wrap;gap:10px}}
.sw{{width:104px}}
.sw i{{display:block;height:50px;border-radius:3px;border:1px solid rgba(255,255,255,.09)}}
.sw span{{display:block;margin-top:6px;font-family:"IBM Plex Mono",monospace;font-size:.58rem;color:var(--ink-3)}}
.sw span b{{display:block;color:var(--ink-2);letter-spacing:.1em;text-transform:uppercase;font-size:.56rem;font-weight:500}}
.directives{{margin:0;padding:0;list-style:none;counter-reset:d}}
.directives li{{position:relative;padding:10px 0 10px 42px;border-top:1px solid var(--line);font-size:.92rem;color:var(--ink-2)}}
.directives li:last-child{{border-bottom:1px solid var(--line)}}
.directives li::before{{counter-increment:d;content:counter(d);position:absolute;left:0;top:9px;
  font-family:"IBM Plex Mono",monospace;font-size:.7rem;width:26px;height:22px;display:grid;place-items:center;
  border:1px solid rgba(var(--accent-rgb),.3);border-radius:2px;color:var(--accent)}}
.directives li b{{color:var(--ink);font-weight:600}}
.wiring{{padding:88px 0 40px}}
.wiring h2{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(1.9rem,4.4vw,2.9rem);margin:0 0 22px}}
.wiring-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:4px;overflow:hidden}}
.wiring-grid section{{background:var(--panel);padding:20px}}
.wiring-grid h4{{margin:0 0 8px;font-size:.95rem;font-weight:600}}
.wiring-grid p{{margin:0;font-size:.9rem;color:var(--ink-2)}}
.risk{{margin:26px 0 0;border:1px solid rgba(var(--accent-rgb),.35);border-left:2px solid var(--accent);
  background:var(--panel);border-radius:3px;padding:16px 18px;max-width:72ch;font-size:.94rem;color:var(--ink-2)}}
.risk b{{color:var(--ink);font-weight:600}}
footer{{border-top:1px solid var(--line);padding:26px 0 60px;font-family:"IBM Plex Mono",monospace;font-size:.66rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}}
</style>"""
