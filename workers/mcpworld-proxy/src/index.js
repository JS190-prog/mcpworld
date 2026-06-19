export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const route = parseMcpworldRoute(url.pathname, env);

    if (!route) {
      return new Response("MCPWorld proxy. Use /mcpworld/{key}/mcp.", {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    const upstreamOrigin = (env.MCPWORLD_UPSTREAM_ORIGIN || "https://www.tornado616.cloud").replace(/\/$/, "");
    const upstream = new URL("/mcpworld/mcp", upstreamOrigin);
    upstream.searchParams.set("key", route.key);

    for (const [name, value] of url.searchParams.entries()) {
      if (name.toLowerCase() !== "key") upstream.searchParams.set(name, value);
    }

    const headers = new Headers(request.headers);
    headers.set("host", upstream.host);
    headers.set("x-mcpworld-proxy", "cloudflare-worker");
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ipcountry");
    headers.delete("cf-ray");

    const init = {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    };

    return fetch(new Request(upstream, init));
  },
};

function parseMcpworldRoute(pathname, env) {
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "mcpworld") return null;

  if (parts.length >= 3 && parts[2] === "mcp") {
    return { key: parts[1] };
  }

  if (parts.length >= 2 && parts[1] === "mcp" && env.MCPWORLD_CONNECTOR_KEY) {
    return { key: env.MCPWORLD_CONNECTOR_KEY };
  }

  return null;
}
