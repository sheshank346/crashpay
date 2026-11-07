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
