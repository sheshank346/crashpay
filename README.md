# Crashpay

Crashpay attacks a checkout in the PayPal sandbox and then checks what happened. When an attack gets through, an LLM proposes a patch and the same attacks are run again to grade it.

Built for the PayPal AI Hackathon 2026. Sandbox only: no real money moves, and the code only talks to api-m.sandbox.paypal.com.

Demo video: ADD THE YOUTUBE LINK HERE

## Why I built it

Most of the PayPal projects I came across were shopping or payment agents. I wanted to test the payment code underneath instead. While trying the sandbox I found that sending the same payment twice without a PayPal-Request-Id creates two separate charges. That made me want a tool that measures this from PayPal's own records, so Crashpay does that, and then checks whether an AI-written fix really holds.

## How it works

1. Attack: Crashpay sends attacks to a shop over HTTP.
2. Scoreboard: payment attacks are checked against PayPal's order records, and input attacks are judged by the shop's HTTP replies.
3. AI patch: a failed attack and the shop's code go to the model (gpt-oss-120b through Groq), which writes a patched shop to a new file.
4. Review: I read the patch, then start it as a new shop. Nothing runs unread.
5. Re-attack: the same attacks grade the patch. If it fails, I describe the failure and go back to step 3.

## What it tests

16 attack classes, 77 test cases per shop, against 6 shops: 96 results per run.

Checked against PayPal's order records (Crashpay fetches each order with GET /v2/checkout/orders/{id} and counts captures with status COMPLETED, or reads the amount):

- Retry after a timeout: the same cart is sent twice, one request after the other.
- Double submit: two identical requests at the same moment.
- Burst submit: eight identical requests at the same moment.
- Price tampering: a $300 monitor is requested with a price of 0.01.
- Price field fuzz: eight valid but wrong prices are sent for the monitor, and the amount PayPal recorded must be 300.00.
- Cart reused for another item: one cart is used for a hub and then a monitor.
- Cart reuse race: the same two items are sent at the same moment.
- 3 carts x 4 requests: twelve requests on three carts must produce exactly three charges.
- Legitimate purchases (control): six different valid carts must all be charged. This stops a shop that refuses everything from scoring well.

Checked against both the shop's reply and PayPal's records:

- Refused request poisons cart: a bad request for a cart must not stop the same cart from being bought afterwards.

Judged by the shop's HTTP replies (a 4xx refusal passes, a 5xx crash or a dropped connection fails):

- Malformed input: incomplete bodies and invalid JSON.
- Type confusion: lists, objects and null where a string should be.
- Fuzz: 35 bad request bodies, including non-objects, missing, empty and wrong-type fields, odd strings, very large values and blank cart ids. It also counts bodies the shop accepted.
- Odd cart ids: eight cart ids with newlines, spaces, an emoji or a very long string. It passes if the shop does not crash. Accepting the id is allowed.
- Replay returns original order: a repeated request must get the first order's id back.
- Oversized body: a 2 MB request must be refused.

Two more checks live in checks.py and are not part of the page: whether a repeated request gets the original order back, and whether a shop charges twice after it is restarted.

The capture status is what counts, not the order status, because a declined card still returns an order marked COMPLETED with a DECLINED capture inside it.

## The six demo shops

All six are written for this project. They run on localhost and take the same request: POST /pay with item, price and cart_id.

- Vulnerable shop (port 5001): trusts the price from the browser, sends no request id to PayPal, has no input checks and no size limit.
- Hand-fixed shop (5002): takes the price from its own list, validates input, locks each cart, sends the cart id to PayPal as the request id, accepts only cart ids of 1 to 64 letters, digits, dashes and underscores, and refuses bodies over 100 KB. Crashpay found bugs in it several times, and each time I repaired it.
- AI-patched shops v1 to v4 (5004 to 5007): written by openai/gpt-oss-120b through Groq.

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

Open http://127.0.0.1:5000, choose how many runs per attack and click Run all attacks. One run of all 96 results takes about three minutes.

Restart the shops before a measured run. The hand-fixed and patched shops remember cart ids while they are running, so a second run can hide a result that the first run showed.

Command line:

## Results

All numbers come from runs I did against the PayPal sandbox on 8 November 2026, on shops I restarted first. They are small samples: every cell below is one run unless it says otherwise.

### All 16 attack classes, one run, final code

P means the shop defended, FAIL means it did not.

| Attack class | Vulnerable | Hand-fixed | AI v1 | AI v2 | AI v3 | AI v4 |
|---|---|---|---|---|---|---|
| Retry after a timeout | FAIL | P | P | P | P | P |
| Double submit | FAIL | P | P | P | P | P |
| Burst submit (8) | FAIL | P | P | P | P | P |
| Price tampering | FAIL | P | P | P | P | P |
| Price field fuzz (8 values) | FAIL | P | P | P | P | P |
| Cart reused for another item | FAIL | P | P | P | P | P |
| Cart reuse race (2 items) | FAIL | P | P | P | P | P |
| 3 carts x 4 requests | FAIL | P | P | P | P | P |
| Legitimate purchases (control) | P | P | P | P | P | P |
| Refused request poisons cart | P | P | P | P | P | P |
| Malformed input | FAIL | P | P | P | P | P |
| Type confusion | FAIL | P | FAIL | P | P | P |
| Fuzz (35 bad bodies) | FAIL | P | FAIL | FAIL | FAIL | P |
| Odd cart ids | P | P | P | P | P | P |
| Replay returns original order | FAIL | P | FAIL | FAIL | FAIL | FAIL |
| Oversized body (2 MB) | FAIL | P | FAIL | FAIL | FAIL | FAIL |
| Defended | 3 of 16 | 16 of 16 | 12 of 16 | 13 of 16 | 13 of 16 | 14 of 16 |

What the vulnerable shop did: 2 charges for one cart on retry, 2 on double submit, 8 charges from 8 simultaneous requests, a $300 monitor sold for 0.01, all 8 wrong prices charged as sent (from 0.02 to 9999.00), and 12 charges from 12 requests on 3 carts. It passes three classes because they do not test what it lacks: the control, odd cart ids (it accepts them without crashing) and the poisoned-cart check.

The hand-fixed shop's 16 of 16 is not independent evidence. I repaired it against these same attacks over several rounds, so it passes the tests it was repaired against.

### Fuzz, in detail

35 bad request bodies, one run each. A body "got through" if the shop crashed on it or accepted it. A good shop refuses every one with a 4xx reply.

| Shop | Refused | Crashed | Accepted | Got through |
|---|---|---|---|---|
| Vulnerable | 18 | 17 | 0 | 17 |
| Hand-fixed | 35 | 0 | 0 | 0 |
| AI v1 | 22 | 7 | 6 | 13 |
| AI v2 | 31 | 0 | 4 | 4 |
| AI v3 | 33 | 0 | 2 | 2 |
| AI v4 | 35 | 0 | 0 | 0 |

Across the four AI patches, the bodies that got through fell from 13 to 4 to 2 to 0. The accepted ones were all cart id problems. From the 409 replies in a follow-up check, I read v1 as accepting an empty string, null, true, 0, 1.5 and a string of spaces, v2 as accepting the empty string, true, 0 and spaces, and v3 as accepting true and 0. That is my reading of the replies, and I did not read the shops' logs for it.

### Timing attacks, repeated

| Shop | Double submit | Burst (8) |
|---|---|---|
| Hand-fixed | 20/20 | 20/20 |
| AI v4 | 20/20 | 20/20 |

20/20 means exactly one charge in every run. The vulnerable shop failed the retry attack in all 10 runs I repeated (2 charges every time). An earlier version of the hand-fixed shop, which relied on the PayPal-Request-Id header alone, defended double submit 7 of 10 times in one test and 4 of 5 in another. I repaired it afterwards.

The other attacks send the same bodies every time, so repeating them tells you nothing new.

### Replay and restart checks

| Check | Hand-fixed | AI v4 |
|---|---|---|
| A repeated request returns the original order | Yes | No: the repeat is refused and no order id comes back |
| Charges for one cart across a restart | 1, the original order came back (2 checks) | 2, a second order was created (1 check) |

The hand-fixed shop sends the cart id to PayPal as the request id, so after a restart PayPal recognised the repeat and returned the original order. v4 forgets its carts on restart and sends no request id, so nothing recognises the repeat. For the hand-fixed shop I inferred from the shop's log that the restarts took place. The restart check is not part of the page.

    python -m crashpay.runner
    python measure.py "fixed shop" "double submit" 20
    python checks.py replay "fixed shop"

measure.py runs one attack against one shop the number of times you give it. The restart check is three steps: python checks.py buy "fixed shop", then restart that shop, then python checks.py again "fixed shop".

## What Crashpay found

About PayPal's sandbox, from my own runs:

- Sending the same payment twice without a PayPal-Request-Id created two separate orders and two charges. Sending the same request id twice returned the same order.
- Capturing one order twice recorded one capture (one test).
- A declined card still returns an order whose status is COMPLETED. The capture inside it says DECLINED. This is why Crashpay counts captures and does not trust the order status.

About the hand-fixed shop, the one I wrote myself and thought was fixed. Crashpay found a bug in it six times, and I repaired each one:

1. It relied on the PayPal-Request-Id header alone, and under simultaneous duplicate requests a second charge got through in some runs (7 of 10 defended in one test, 4 of 5 in another). I do not know why the header was not enough. I fixed it by giving each cart its own lock and returning the first reply on a repeat.
2. It crashed with HTTP 500 when a request had an item but no cart id.
3. It crashed with HTTP 500 when the item was a list.
4. It crashed when the cart id was only spaces.
5. It crashed on cart ids with a newline, a leading space, an emoji or a right-to-left character. The shop sends the cart id to PayPal as the request id header, and the requests library refuses those characters in a header. I now accept only cart ids of 1 to 64 letters, digits, dashes and underscores.
6. It accepted a 2 MB request body. It now refuses bodies over 100 KB.

About the AI patches:

- Each patch passed the attacks that existed when it was written and failed a later one. v1 failed type confusion and 13 fuzz bodies, v2 and v3 accepted bad cart ids (4 bodies, then 2), and v4 passes the fuzz attack.
- None of the four patches refuses a 2 MB body, and none returns the original order when a request is repeated. They keep carts in memory and send no request id to PayPal.
- v4 charged a second time after a restart (1 check), because it forgets its carts and sends no request id.
- A patch is only as good as the attacks that grade it. The restart check, the replay check and the size check each found a gap that the first seven attack classes did not. Adding an attack and grading a patch again takes minutes, and that is the useful part of this project.

A note on PayPal's agent toolkit: in paypal-agent-toolkit 1.11.0 for Python, I found no PayPal-Request-Id in the headers it builds, and its pay_order tool takes only an order id. I only read the code. I did not run payments through the toolkit, so I do not know whether it causes a duplicate charge.

## What is simulated, and what is not

Real: every order, capture and amount comes from PayPal's sandbox API, and the shops call the sandbox for every payment. No payment result is invented or mocked.

Not real:

- It is the sandbox. The money is fake, and production timing and rules may differ.
- The payer is a PayPal test card sent through the Orders API. I tried PayPal's saved-wallet API, which would let an agent pay on a buyer's behalf, but the permission was refused for my app (HTTP 403).
- The shops are mine. Crashpay tests a checkout that accepts POST /pay with item, price and cart_id. Pointing it at another checkout would need an adapter that I did not write.

## Limits

- Small samples. Every cell in the main table is one run. The timing attacks were repeated 20 times on two shops, and the restart and replay checks were done once or twice.
- Eight of the 16 classes are judged by the shop's HTTP replies and not by PayPal's records. Those send the same bodies every time, so repeating them tells you nothing new.
- The hand-fixed shop's 16 of 16 is not independent: I repaired it against these same attacks.
- The test cases are ones I thought of. The fuzz catalog missed bad cart ids until I added them, and four of my own tests (odd cart ids, oversized body, price fuzz and the legitimate-purchase control) needed corrections after I found mistakes in them.
- Webhooks are not tested, and neither are forged or replayed notifications.
- I did not test several server processes, a shared database or any production setup.
- I told the model what had failed in rounds v2 to v4, so the fixer is a way to grade patches. It did not find the failures itself.
- python -m crashpay.runner prints only the first nine classes. The page runs all 16.
- One early run of the vulnerable shop's retry attack showed an error once. It did not come back in 10 later runs, and I did not find the cause.
- Windows only, as far as I tested.

## AI tools used

- In the product: openai/gpt-oss-120b, called through Groq, writes the patches in fixer.py. AI plays no part in scoring an attack.
- During development: I used Claude (Anthropic) as an assistant for writing code, debugging . I ran every command myself, read every patch before running it, and checked the results against PayPal's records and the shops' logs.

## What I would do next

- Test webhook replay and forged notifications.
- Let you point Crashpay at a checkout it did not come with, through a settings file for the URL, the field names and the order id.
- Give the shops a database, add the restart check to the page, and run another patch round against it.
- Repeat every attack many more times.

## Files

- crashpay/paypal.py: the sandbox API calls
- crashpay/attacks.py, attacks2.py and cases.py: the attacks and the fuzz bodies
- crashpay/shop.py: the vulnerable and hand-fixed shops
- crashpay/vuln_shop.py: the source the first patch was generated from
- crashpay/patched_shop.py to patched_shop_v4.py: the model's patches, as generated
- crashpay/fixer.py and llm.py: the patch generator
- crashpay/web.py and static/index.html: the page
- checks.py, measure.py, start_all.bat, run_shop.py: command line tools

## License

MIT. This is an independent project and is not affiliated with or endorsed by PayPal.
