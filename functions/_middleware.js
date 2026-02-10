export async function onRequest(context) {
  const url = new URL(context.request.url);
  const { next } = context;

  // 1. Canonical Redirects: Strip .html and handle trailing slashes
  // If the path ends in .html, redirect to the path without it
  if (url.pathname.endsWith('.html')) {
    url.pathname = url.pathname.slice(0, -5);
    return Response.redirect(url.toString(), 301);
  }

  // If the path does NOT end in / and allows for it (not a file), we might want to enforce a standard
  // For now, let's just stick to the .html stripping as the primary canonical rule.
  
  // 2. Fetch the asset or next middleware
  const response = await next();

  // 3. Add Security Headers
  const newResponse = new Response(response.body, response);
  
  newResponse.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
  newResponse.headers.set("X-Frame-Options", "DENY");
  newResponse.headers.set("X-Content-Type-Options", "nosniff");
  newResponse.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  newResponse.headers.set("Permissions-Policy", "geolocation=(self), microphone=(), camera=(), payment=()");

  return newResponse;
}
