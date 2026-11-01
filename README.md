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


## Results

Every number here comes from runs I did myself against the PayPal sandbox. Each cell is attacks defended out of runs, so 5/5 means the shop held up all five times and 0/5 means it failed every time.

First 5-run test, before I repaired the hand-fixed shop:

| Shop | Retry after a timeout | Double submit | Price tampering | Malformed input |
|---|---|---|---|---|
| Vulnerable | 0/5 | 0/5 | 0/5 | 0/5 |
| Hand-fixed (first version) | 5/5 | 4/5 | 5/5 | 0/5 |
| LLM-patched | 5/5 | 5/5 | 5/5 | 5/5 |

I ran double submit ten times on its own against two of the shops: the first version of the hand-fixed shop defended 7 of 10, and the LLM-patched shop defended 10 of 10.

After I repaired the hand-fixed shop, one more 5-run test gave 5/5 on all four attacks for both the hand-fixed and the LLM-patched shop. In that same run the vulnerable shop's retry row showed an error. The three other vulnerable rows worked, and I did not find the cause.

These are small samples from the sandbox. A different number of runs, or production timing, could give different results.

## What Crashpay found

Crashpay found two bugs in the shop I had written myself and thought was fixed.

1. It relied only on the PayPal-Request-Id header to stop duplicates. When two identical requests arrived at the same moment, a second charge sometimes went through.
2. It crashed with HTTP 500 on a request that had an item but no cart id, because it never checked that the field existed.

I repaired it by validating the input, giving each cart its own lock, and returning the first reply when the same cart is submitted again. It still sends the cart id to PayPal as the request id, as a second layer.

The LLM-patched shop took a different approach. It keeps a set of cart ids in memory and refuses a repeat with a 409 response. It does not send a request id to PayPal. That worked in my tests, but the memory is lost when the server restarts, and it would not work across several server processes. It also gives a repeated request an error and not the original order.

