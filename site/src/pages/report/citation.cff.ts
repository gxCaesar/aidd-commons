import citation from "../../../../CITATION.cff?raw";

export function GET() {
  return new Response(citation, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
