# Crashpay



Crashpay attacks a checkout in the PayPal sandbox and reports what happened using PayPal's own order records. When an attack succeeds, an LLM writes a patch and the same attacks are run again to check it.



Built for the PayPal AI Hackathon 2026. Sandbox only: no real money moves, and the code only talks to api-m.sandbox.paypal.com.



## Why I built it



Most of the PayPal projects I came across were shopping or payment agents. I wanted to test the payment code underneath instead. While trying the sandbox I found that sending the same payment twice without a PayPal-Request-Id creates two separate charges. That made me want a tool that measures this from PayPal's own records, so Crashpay does that, and then checks whether an AI-written fix really holds.



## What it does



Crashpay runs four attacks against demo shops and counts what PayPal actually recorded.



- Retry after a timeout: the same cart is submitted twice, the way an agent would after a hung request. Crashpay counts how many charges PayPal recorded.

- Double submit: two identical requests are sent at the same moment.

- Price tampering: a $300 monitor is requested with a price of 0.01. Crashpay reads the amount back from the PayPal order.

- Malformed input: incomplete or broken requests are sent. A server crash (HTTP 500) counts as a failure.



The targets are three demo shops written for this project:



- a vulnerable shop with the bugs left in on purpose

- a shop fixed by hand

- a shop patched by an LLM (openai/gpt-oss-120b, called through Groq)



Every result comes from PayPal. After each attack, Crashpay fetches the orders from GET /v2/checkout/orders/{id} and counts the captures with status COMPLETED.

