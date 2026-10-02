from django.http import HttpResponse


def mobile_api_docs(request):
    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Jobell Mobile API</title>
  <style>
    :root { --bg:#f6f7f9; --panel:#fff; --ink:#17202a; --muted:#667085; --line:#d9dee7; --gold:#b88720; --green:#138a52; --blue:#2764c9; --red:#c33b32; --violet:#6b4bd8; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin:0; background:var(--bg); color:var(--ink); }
    header { background:#101820; color:#fff; padding:32px clamp(18px,5vw,64px); }
    h1,h2,p { margin:0; } h1 { font-size:clamp(28px,4vw,44px); } h2 { font-size:18px; margin-bottom:12px; }
    header p { color:#d6dde7; margin-top:10px; max-width:760px; }
    main { display:grid; gap:18px; padding:24px clamp(14px,4vw,48px) 48px; }
    .toolbar,.section,.endpoint { background:var(--panel); border:1px solid var(--line); border-radius:8px; }
    .toolbar { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; padding:16px; }
    .base { display:flex; align-items:center; justify-content:space-between; gap:10px; border:1px solid var(--line); border-radius:6px; padding:10px 12px; background:#fbfcfe; }
    code { font-family:"Cascadia Code", Consolas, monospace; font-size:13px; overflow-wrap:anywhere; }
    button { border:1px solid var(--line); background:#fff; border-radius:6px; padding:7px 10px; cursor:pointer; font-weight:650; }
    button:hover { border-color:var(--gold); color:var(--gold); }
    .section { padding:18px; } .grid { display:grid; gap:10px; }
    .endpoint { display:grid; grid-template-columns:88px 1fr auto; gap:10px; align-items:center; padding:12px; }
    .method { border-radius:6px; color:#fff; font-size:12px; font-weight:800; padding:7px 8px; text-align:center; }
    .GET{background:var(--green)} .POST{background:var(--blue)} .PATCH,.PUT{background:var(--violet)} .DELETE{background:var(--red)}
    .path { font-weight:750; } .meta { color:var(--muted); font-size:13px; margin-top:3px; }
    pre { background:#111827; color:#e5e7eb; border-radius:8px; padding:14px; overflow-x:auto; margin:10px 0 0; }
    .auth { color:#744d00; background:#fff7e1; border:1px solid #efd285; border-radius:999px; padding:4px 8px; font-size:12px; font-weight:750; white-space:nowrap; }
    @media (max-width:720px){ .endpoint{grid-template-columns:72px 1fr} .endpoint button{grid-column:1/-1} }
  </style>
</head>
<body>
  <header><h1>Jobell Mobile API</h1><p>Use these endpoints from the Jobell mobile app. Protected routes require Authorization: Bearer &lt;access_token&gt;.</p></header>
  <main>
    <section class="toolbar">
      <div class="base"><code>http://localhost:8000/api/v1/</code><button data-copy="http://localhost:8000/api/v1/">Copy</button></div>
      <div class="base"><code>http://10.0.2.2:8000/api/v1/</code><button data-copy="http://10.0.2.2:8000/api/v1/">Copy</button></div>
      <div class="base"><code>http://YOUR_PC_IP:8000/api/v1/</code><button data-copy="http://YOUR_PC_IP:8000/api/v1/">Copy</button></div>
    </section>
    <section class="section"><h2>Auth</h2><div class="grid">
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/auth/register/</div><div class="meta">Create account</div></div><button data-copy="/auth/register/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/auth/login/</div><div class="meta">Returns user and JWT tokens</div></div><button data-copy="/auth/login/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/auth/me/ <span class="auth">Bearer</span></div><div class="meta">Current user</div></div><button data-copy="/auth/me/">Copy</button></div>
      <div class="endpoint"><span class="method PATCH">PATCH</span><div><div class="path">/auth/me/ <span class="auth">Bearer</span></div><div class="meta">Update profile</div></div><button data-copy="/auth/me/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/auth/logout/ <span class="auth">Bearer</span></div><div class="meta">Blacklist refresh token</div></div><button data-copy="/auth/logout/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/auth/token/refresh/</div><div class="meta">Refresh access token</div></div><button data-copy="/auth/token/refresh/">Copy</button></div>
    </div><pre>{\n  "email": "user@example.com",\n  "password": "password123"\n}</pre></section>
    <section class="section"><h2>Catalog</h2><div class="grid">
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/categories/</div><div class="meta">List categories</div></div><button data-copy="/categories/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/categories/{id}/</div><div class="meta">Category detail</div></div><button data-copy="/categories/{id}/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/products/</div><div class="meta">Supports search, category, is_featured, ordering</div></div><button data-copy="/products/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/products/{slug}/</div><div class="meta">Product detail with variants and images</div></div><button data-copy="/products/{slug}/">Copy</button></div>
    </div></section>
    <section class="section"><h2>Cart, Checkout, Orders</h2><div class="grid">
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/cart/ <span class="auth">Bearer</span></div><div class="meta">Current cart</div></div><button data-copy="/cart/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/cart-items/ <span class="auth">Bearer</span></div><div class="meta">Add variant to cart</div></div><button data-copy="/cart-items/">Copy</button></div>
      <div class="endpoint"><span class="method PATCH">PATCH</span><div><div class="path">/cart-items/{id}/ <span class="auth">Bearer</span></div><div class="meta">Update quantity</div></div><button data-copy="/cart-items/{id}/">Copy</button></div>
      <div class="endpoint"><span class="method DELETE">DELETE</span><div><div class="path">/cart-items/{id}/ <span class="auth">Bearer</span></div><div class="meta">Remove item</div></div><button data-copy="/cart-items/{id}/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/checkout/summary/ <span class="auth">Bearer</span></div><div class="meta">Totals and delivery fee</div></div><button data-copy="/checkout/summary/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/orders/checkout/ <span class="auth">Bearer</span></div><div class="meta">Create order</div></div><button data-copy="/orders/checkout/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/orders/ <span class="auth">Bearer</span></div><div class="meta">Customer orders</div></div><button data-copy="/orders/">Copy</button></div>
    </div><pre>{\n  "variant_id": 1,\n  "quantity": 2\n}</pre></section>
    <section class="section"><h2>Addresses And Wishlist</h2><div class="grid">
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/addresses/ <span class="auth">Bearer</span></div><div class="meta">List saved addresses</div></div><button data-copy="/addresses/">Copy</button></div>
      <div class="endpoint"><span class="method POST">POST</span><div><div class="path">/addresses/ <span class="auth">Bearer</span></div><div class="meta">Create address</div></div><button data-copy="/addresses/">Copy</button></div>
      <div class="endpoint"><span class="method GET">GET</span><div><div class="path">/wishlist-items/ <span class="auth">Bearer</span></div><div class="meta">List wishlist items</div></div><button data-copy="/wishlist-items/">Copy</button></div>
    </div></section>
  </main>
  <script>document.querySelectorAll('button[data-copy]').forEach((b)=>b.addEventListener('click',async()=>{await navigator.clipboard.writeText(b.dataset.copy);const t=b.textContent;b.textContent='Copied';setTimeout(()=>b.textContent=t,900)}));</script>
</body>
</html>'''
    return HttpResponse(html)
