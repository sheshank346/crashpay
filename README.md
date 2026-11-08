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

    python -m crashpay.runner
    python measure.py "fixed shop" "double submit" 20
    python checks.py replay "fixed shop"

measure.py runs one attack against one shop the number of times you give it. The restart check is three steps: python checks.py buy "fixed shop", then restart that shop, then python checks.py again "fixed shop".
