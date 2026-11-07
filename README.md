# Crashpay

Crashpay attacks a checkout in the PayPal sandbox and then checks what happened. When an attack gets through, an LLM proposes a patch and the same attacks are run again to grade it.

Built for the PayPal AI Hackathon 2026. Sandbox only: no real money moves, and the code only talks to api-m.sandbox.paypal.com.

Demo video: ADD THE YOUTUBE LINK HERE

## Why I built it

Most of the PayPal projects I came across were shopping or payment agents. I wanted to test the payment code underneath instead. While trying the sandbox I found that sending the same payment twice without a PayPal-Request-Id creates two separate charges. That made me want a tool that measures this from PayPal's own records, so Crashpay does that, and then checks whether an AI-written fix really holds.

## What it does

Crashpay sends attacks over HTTP to demo shops. Seven attacks are built in:

- Retry after a timeout: the same cart is sent twice, one request after the other.
- Double submit: two identical requests at the same moment.
- Burst submit: eight identical requests at the same moment.
- Price tampering: a $300 monitor is requested with a price of 0.01.
- Malformed input: incomplete bodies and invalid JSON.
- Type confusion: lists, objects and null where a string should be.
- Fuzz: 35 bad request bodies, including non-objects, missing, empty and wrong-type fields, odd strings, very large values and blank cart ids.

How a result is read depends on the attack. For the first four, Crashpay asks PayPal what was recorded: it fetches the orders with GET /v2/checkout/orders/{id} and counts captures with status COMPLETED, and for price tampering it reads the amount from the order. It looks at the capture status and not the order status, because a declined card still returns an order marked COMPLETED with a DECLINED capture inside it. The last three attacks are judged by the shop's HTTP replies: a refusal (4xx) passes, a crash (5xx) or a dropped connection fails, and fuzz also counts bodies the shop accepted.

Two more checks live in checks.py and are not part of the page: whether a repeated request gets the original order back, and whether a shop charges twice after it is restarted.

## The six demo shops

All six are written for this project. They run on localhost and take the same request: POST /pay with item, price and cart_id.

- Vulnerable shop (port 5001): trusts the price from the browser, sends no request id to PayPal, and has no input checks.
- Hand-fixed shop (5002): takes the price from its own list, validates input, locks each cart, and sends the cart id to PayPal as the request id. I repaired it several times after Crashpay found bugs in it.
- AI-patched shops v1 to v4 (5004 to 5007): written by openai/gpt-oss-120b through Groq (see below).

## The AI fixer

fixer.py sends a description of a failed attack and the shop's source code to the model and saves the code block from its answer as a new file. It never overwrites a shop, and I read every patch before running it. v1 was generated from the vulnerable shop. For v2, v3 and v4 I gave the model the previous patch and described the failure and the rule it broke, for example that an empty cart id must be refused with a 4xx reply. So the model did not find the failures on its own: the attacks did, and the model fixed what I described.

## How to run it

Tested on Windows with Python 3.14. I have not tried macOS or Linux.

    git clone https://github.com/sheshank346/crashpay.git
    cd crashpay
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env

Then put your sandbox Client ID and Secret in .env. You need a sandbox business account, a REST app linked to it, and card payments available on that app. Create the sandbox accounts with the country set to United States: my first accounts were created for India, and PayPal's checkout page failed for them. To use the fixer, add a line GROQ_API_KEY=... to .env. The .env file is ignored by Git.

Start everything with one command, which opens seven windows (six shops and the web page):

    start_all.bat

Open http://127.0.0.1:5000, choose how many runs per attack and click Run all attacks. One run of every attack against every shop takes about a minute.

Restart the shops before a measured run. The hand-fixed and patched shops remember cart ids while they are running, so a second run can hide a result that the first run showed.

Command line:

    python -m crashpay.runner
    python measure.py "fixed shop" "double submit" 20
    python checks.py replay "fixed shop"

measure.py runs one attack against one shop the number of times you give it. The restart check is three steps: python checks.py buy "fixed shop", then restart that shop, then python checks.py again "fixed shop".




## Results

All numbers come from runs I did against the PayPal sandbox in November 2026, on shops I restarted first. Each table says what was measured. These are small samples.

### One run of every attack on freshly started shops

| Shop | Retry | Double submit | Burst (8) | Price tampering | Malformed | Type confusion | Fuzz |
|---|---|---|---|---|---|---|---|
| Vulnerable | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| Hand-fixed | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| AI-patched v1 | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL |
| AI-patched v2 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL |
| AI-patched v3 | PASS | PASS | PASS | PASS | PASS | PASS | FAIL |
| AI-patched v4 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

What the vulnerable shop did: 2 charges for one cart on retry, 2 charges on double submit, 8 charges from 8 simultaneous requests, and a $300 monitor sold for 0.01. It crashed (HTTP 500) on 17 of the 35 fuzz bodies.

### Fuzz detail (35 bad request bodies, one run each)

A body counts as "got through" if the shop crashed on it or accepted it. A good shop refuses every one with a 4xx reply.

| Shop | Refused | Crashed | Accepted | Got through |
|---|---|---|---|---|
| Vulnerable | 18 | 17 | 0 | 17 |
| Hand-fixed | 35 | 0 | 0 | 0 |
| AI-patched v1 | 22 | 7 | 6 | 13 |
| AI-patched v2 | 31 | 0 | 4 | 4 |
| AI-patched v3 | 33 | 0 | 2 | 2 |
| AI-patched v4 | 35 | 0 | 0 | 0 |

The accepted bodies were all cart id problems. From the 409 replies in a follow-up check, I read v1 as accepting an empty string, null, true, 0, 1.5 and a string of spaces, v2 as accepting the empty string, true, 0 and spaces, and v3 as accepting true and 0. I inferred this from the replies and did not read the shops' logs.

The malformed input, type confusion and fuzz attacks send the same bodies every time, so repeating them tells you nothing new. Repeating helps only for the timing attacks below.

### Timing attacks, repeated

| Shop | Double submit | Burst (8) |
|---|---|---|
| Hand-fixed | 20/20 | 20/20 |
| AI-patched v4 | 20/20 | 20/20 |

20/20 means exactly one charge in every run. Earlier, the first version of the hand-fixed shop, which relied on the PayPal-Request-Id header alone, defended double submit 7 of 10 times in one test and 4 of 5 in another. I repaired it afterwards.

### Replay and restart checks

| Check | Hand-fixed | AI-patched v4 |
|---|---|---|
| A repeated request returns the original order | Yes (1 check) | No: the repeat is refused with a 409 and no order id (1 check) |
| Charges for one cart across a restart | 1, the original order came back (2 checks) | 2, a second order was created (1 check) |

The hand-fixed shop sends the cart id to PayPal as the request id, so after a restart PayPal recognised the repeat and returned the original order. v4 forgets its carts on restart and sends no request id, so nothing recognises the repeat.

### Things I did not explain

One early run of the vulnerable shop's retry attack showed an error row once. It did not come back in 10 later runs, which all gave 2 charges, and I did not find the cause. Other error rows on the page came from a shop window I had closed.
