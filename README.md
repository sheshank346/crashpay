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

## What Crashpay found

About PayPal's sandbox, from my own runs:

- Sending the same payment twice without a PayPal-Request-Id created two separate orders and two charges. Sending the same request id twice returned the same order.
- Capturing one order twice recorded one capture (one test).
- A declined card still returns an order whose status is COMPLETED. The capture inside it says DECLINED. This is why Crashpay counts captures and does not trust the order status.

About the shops I wrote:

- My first hand-written fix relied on the request id header alone. Under simultaneous duplicate requests it let a second charge through in some runs (7 of 10 defended in one test, 4 of 5 in another). I do not know why the header was not enough in those runs. I fixed it by giving each cart its own lock and returning the first reply on a repeat.
- It also crashed with HTTP 500 when an item was a list or a cart id was missing or only spaces. Crashpay found each of these, and I fixed them one at a time.

About the AI patches:

- Each patch passed the attacks that existed when it was written and failed a later attack. v1 failed type confusion and 13 fuzz bodies, v2 and v3 accepted bad cart ids (4 bodies, then 2), and v4 passed the whole suite.
- v4 still fails a check the suite did not have: after a restart it charged a second time (1 check). It keeps carts in memory and sends no request id to PayPal.
- So a patch is only as good as the attacks that grade it, and the useful part of this project is that adding an attack and grading the patch again takes minutes.

A note on PayPal's agent toolkit: in paypal-agent-toolkit 1.11.0 for Python, I found no PayPal-Request-Id in the headers it builds, and its pay_order tool takes only an order id. I only read the code. I did not run payments through the toolkit, so I do not know whether it causes a duplicate charge.

## What is simulated, and what is not

Real: every order, capture and amount comes from PayPal's sandbox API, and the shops call the sandbox for every payment. No payment result is invented or mocked.

Not real:

- It is the sandbox. The money is fake, and production timing and rules may differ.
- The payer is a PayPal test card sent through the Orders API. I tried PayPal's saved-wallet API, which would let an agent pay on a buyer's behalf, but the permission was refused for my app (HTTP 403).
- The shops are mine. Crashpay tests a checkout that accepts POST /pay with item, price and cart_id. Pointing it at another checkout would need an adapter that I did not write.

## Limits

- Small samples. Most cells are one run. The timing attacks were repeated 20 times on two shops, and the restart and replay checks were done once or twice.
- The malformed input, type confusion and fuzz attacks are judged by the shop's HTTP replies, not by PayPal's records. They send the same bodies every time.
- The fuzz catalog has 35 bodies that I chose. It finds what I thought of, and it missed bad cart ids until I added them.
- Webhooks are not tested, and neither are forged or replayed notifications.
- I did not test several server processes, a shared database or any production setup.
- I told the model what had failed in rounds v2 to v4, so the fixer is a way to grade patches. It did not find the failures itself.
- Windows only, as far as I tested.

## AI tools used

- In the product: openai/gpt-oss-120b, called through Groq, writes the patches in fixer.py. AI plays no part in scoring an attack.
- During development: I used Claude (Anthropic) as an assistant for writing code, debugging . I ran every command myself, read every patch before running it, and checked the results against PayPal's records and the shops' logs.

## What I would do next

- Test webhook replay and forged notifications.
- Write an adapter so Crashpay can attack a checkout it did not come with.
- Give the shops a database, add the restart check to the page, and run another patch round against it.
- Repeat every attack many more times.

## Files

- crashpay/paypal.py: the sandbox API calls
- crashpay/attacks.py and cases.py: the attacks and the fuzz bodies
- crashpay/shop.py: the vulnerable and hand-fixed shops
- crashpay/patched_shop.py to patched_shop_v4.py: the model's patches, unedited
- crashpay/fixer.py and llm.py: the patch generator
- crashpay/web.py and static/index.html: the page
- checks.py, measure.py, start_all.bat, run_shop.py: command line tools

## License

MIT. This is an independent project and is not affiliated with or endorsed by PayPal.

One early run of the vulnerable shop's retry attack showed an error row once. It did not come back in 10 later runs, which all gave 2 charges, and I did not find the cause. Other error rows on the page came from a shop window I had closed.
