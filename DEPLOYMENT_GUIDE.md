# 🚀 Masumi Make.com Proxy - Deployment Guide

## 📦 What You Have

This is a **simple proxy server** that connects Masumi payment system to your Make.com webhook.

**NO AI models. NO LangChain. Just a lightweight HTTP proxy.**

---

## 🎯 Quick Deploy to Railway (5 Minutes)

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `masumi-makecom-proxy`
3. Set to **Public**
4. Click "Create repository"

### Step 2: Upload Files

Upload these 4 files to your repository:
- `main.py` (the proxy server code)
- `requirements.txt` (Python dependencies)
- `Dockerfile` (container configuration)
- `railway.json` (Railway configuration)

**Via GitHub Web Interface:**
1. Click "Add file" → "Upload files"
2. Drag all 4 files
3. Click "Commit changes"

**Or via command line:**
```bash
git clone https://github.com/YOUR_USERNAME/masumi-makecom-proxy
cd masumi-makecom-proxy

# Copy the 4 files here
# Then:
git add .
git commit -m "Initial commit"
git push
```

### Step 3: Deploy on Railway

1. Go to https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Select your `masumi-makecom-proxy` repository
5. Click **"Deploy"**

### Step 4: Configure Environment Variables

Click on your deployed service → **"Variables"** tab

Add these variables (copy from your notes):

```env
# Payment Service Connection
PAYMENT_SERVICE_URL=https://your-payment-service.railway.app/api/v1
PAYMENT_API_KEY=your_admin_api_key_from_payment_service

# Wallet Configuration
SELLER_VKEY=your_selling_wallet_vkey

# Make.com Integration
MAKE_WEBHOOK_URL=https://hook.us1.make.com/YOUR_WEBHOOK_URL

# Agent Details
AGENT_IDENTIFIER=linkedin-outreach-generator

# Pricing
PAYMENT_AMOUNT=10000000
PAYMENT_UNIT=lovelace

# Port (Railway provides this automatically, but you can set it)
PORT=8000
```

### Step 5: Generate Public Domain

1. Go to **"Settings"** tab
2. Scroll to **"Networking"**
3. Click **"Generate Domain"**
4. Copy your URL: `https://masumi-makecom-proxy-production-xxxx.up.railway.app`

---

## 🧪 Testing Your Deployment

### Test 1: Health Check
```bash
curl https://your-proxy-url.railway.app/health
```
Expected: `{"status":"ok"}`

### Test 2: Availability
```bash
curl https://your-proxy-url.railway.app/availability
```
Expected: `{"status":"available","message":"LinkedIn Outreach Email Generator is online"}`

### Test 3: Input Schema
```bash
curl https://your-proxy-url.railway.app/input_schema
```
Expected: JSON with csv_url field definition

### Test 4: Start Job (Full Flow)
```bash
curl -X POST https://your-proxy-url.railway.app/start_job \
  -H "Content-Type: application/json" \
  -d '{
    "identifier_from_purchaser": "test@example.com",
    "input_data": [
      {"key": "csv_url", "value": "https://example.com/contacts.csv"}
    ]
  }'
```

Expected response:
```json
{
  "status": "success",
  "job_id": "uuid-here",
  "paymentAddress": "addr_test1...",
  "requiredAmount": "10000000 lovelace",
  "blockchainIdentifier": "..."
}
```

### Test 5: Pay and Check Status

1. Send 10 ADA to the payment address (use wallet from admin panel)
2. Wait 1-2 minutes for blockchain confirmation
3. Check status:

```bash
curl https://your-proxy-url.railway.app/status?job_id=YOUR_JOB_ID
```

Expected final response:
```json
{
  "job_id": "...",
  "status": "completed",
  "result": {
    "success": true,
    "filename": "outreach_emails.csv",
    "csv_text": "...",
    ...
  }
}
```

---

## 📋 Environment Variables Explained

| Variable | Description | Example |
|----------|-------------|---------|
| `PAYMENT_SERVICE_URL` | Your Masumi Payment Service API URL | `https://masumi-payment-xxx.railway.app/api/v1` |
| `PAYMENT_API_KEY` | Admin API key from payment service | From payment service Variables tab |
| `SELLER_VKEY` | Your selling wallet verification key | From payment service admin panel |
| `MAKE_WEBHOOK_URL` | Your Make.com webhook URL | `https://hook.us1.make.com/xxx` |
| `AGENT_IDENTIFIER` | Unique agent ID | `linkedin-outreach-generator` |
| `PAYMENT_AMOUNT` | Price in lovelace (1 ADA = 1,000,000) | `10000000` (10 ADA) |
| `PAYMENT_UNIT` | Currency unit | `lovelace` |
| `PORT` | Server port | `8000` |

---

## 🎯 Next Steps: Register on Masumi

Once your proxy is deployed and tested:

### Option A: Via Payment Service Admin Panel

1. Open: `https://your-payment-service.railway.app/admin`
2. Login with admin credentials
3. Go to "Agents" section
4. Click "Register New Agent"
5. Fill in:
   - **Name:** LinkedIn Outreach Email Generator
   - **URL:** `https://your-proxy-url.railway.app`
   - **Description:** Generates personalized outreach emails from LinkedIn profiles
   - **Price:** 10 ADA per file
6. Click "Submit"

### Option B: Via API Call

```bash
curl -X POST "https://your-payment-service.railway.app/api/v1/registry" \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LinkedIn Outreach Email Generator",
    "url": "https://your-proxy-url.railway.app",
    "description": "Generates personalized outreach emails from LinkedIn profiles",
    "category": "marketing",
    "seller_vkey": "YOUR_SELLING_WALLET_VKEY",
    "pricing": {
      "amount": "10000000",
      "unit": "lovelace"
    }
  }'
```

Save the `agentIdentifier` from the response!

---

## 🛍️ List on Sōkosumi Marketplace

1. Go to https://www.sokosumi.com
2. Sign in (connects to your Masumi wallet)
3. Your agent should appear automatically
4. Add marketing materials:
   - Screenshots of Make.com workflow
   - Demo video
   - Use cases
   - Pricing details
5. Publish!

---

## 🔧 Troubleshooting

### "Payment service error"
- Check `PAYMENT_SERVICE_URL` is correct
- Verify `PAYMENT_API_KEY` is valid
- Make sure payment service is running

### "Make.com webhook error"
- Verify `MAKE_WEBHOOK_URL` is correct
- Test Make.com webhook directly
- Check Make.com scenario is active

### "Payment timeout"
- Check wallet has sufficient ADA
- Verify blockchain is not congested
- Try sending payment again

### "Job not found"
- Jobs are stored in memory (cleared on restart)
- For production, use Redis or database

---

## 💰 Cost Summary

**Railway Hosting:**
- Free tier: $5/month credit
- Hobby plan: $5/month (recommended)

**Masumi Network:**
- Registration: ~0.5 ADA (one-time)
- Transaction fees: ~0.17 ADA per payment

**Total monthly cost: $5 + minimal ADA fees**

---

## 📚 Support

- **Masumi Discord:** https://discord.com/invite/aj4QfnTS92
- **Railway Docs:** https://docs.railway.app
- **Make.com Support:** https://www.make.com/en/help

---

## ✅ Deployment Checklist

- [ ] Created GitHub repository
- [ ] Uploaded all 4 files
- [ ] Deployed on Railway
- [ ] Added all environment variables
- [ ] Generated public domain
- [ ] Tested all 4 endpoints
- [ ] Registered agent on Masumi
- [ ] Listed on Sōkosumi marketplace
- [ ] Made first test payment
- [ ] Received CSV output successfully

**🎉 Congratulations! Your agent is now live!**