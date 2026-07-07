# The Academic Edge Pack — Landing Page System

## Files

| File | Purpose |
|------|---------|
| `index.html` | Main landing page with checkout modal + Paystack |
| `server.js` | Express backend — payment verification + email |
| `download.html` | Post-payment download page |
| `ACADEMIC FUNNEL ASSETS/` | Images (book covers, profile, testimonials) |

## Setup

### 1. Install dependencies

```bash
cd "landing page"
npm init -y
npm install express cors dotenv nodemailer
```

### 2. Create `.env` file

```env
PAYSTACK_SECRET_KEY=sk_live_XXXXXXXXXXXXXXXX
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
FROM_EMAIL=Itoya David <your-email@gmail.com>
TOKEN_SECRET=any-random-secret-string
PORT=3000
```

### 3. Replace placeholders

- **`index.html`** — Find `pk_live_XXXXXXXXXXXXXXXX` and replace with your Paystack **public** key
- **`server.js`** — Update the `DOWNLOADS` array with real file URLs (Google Drive, Selar, S3, etc.)
- **`server.js`** — SMTP credentials for email delivery
- **Images** — Place `profileimg.jpg`, `test1.png`, `test2.png`, `bookcover.png` in `ACADEMIC FUNNEL ASSETS/`

### 4. Run

```bash
node server.js
```

Visit `http://localhost:3000`

## Checkout Flow

1. User clicks "Get The Pack" → modal opens
2. Step 1: Enter name + email
3. Step 2: Join WhatsApp community → unlock ₦2,000 price
4. Step 3: Paystack popup processes payment
5. On success → backend verifies → shows download page + sends email

## Production Deployment

- Use PM2 or similar: `npx pm2 start server.js`
- Add nginx reverse proxy for HTTPS
- Replace in-memory `orders` array with a real database (MongoDB, PostgreSQL, etc.)
- Consider using Resend or Mailgun instead of Gmail SMTP for reliability
