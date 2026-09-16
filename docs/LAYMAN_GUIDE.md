# SmartDoc AI Layman Guide

This guide is for someone who just wants to get the app running and use it, without worrying about the technical details.

## What this app does

SmartDoc AI lets you:

- upload a PDF
- ask questions about that PDF
- get answers based only on what is inside the PDF
- see simple usage insights, like how many questions were asked

Think of it like a chat app that reads your PDF first, then answers based on that document.

## Before you start

You need 3 accounts or services:

- a GitHub account
- a Vercel account
- a DeepSeek API key

You also need a Vercel Postgres database.

## What you need to set in Vercel

In your Vercel project, add these environment variables:

### Required

- `DEEPSEEK_API_KEY`
- `POSTGRES_URL`

### Optional

- `DEEPSEEK_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-chat`
- `TOP_K=3`

If you do not set the optional ones, the app already uses those values by default.

## Very simple deployment steps

### 1. Push the code to GitHub

Make sure your repository contains this project.

### 2. Import the repo into Vercel

In Vercel:

1. click `Add New`
2. click `Project`
3. choose your GitHub repository
4. import it

### 3. Add the database

In Vercel:

1. open your project
2. go to the storage section
3. create a `Postgres` database
4. copy the connection string

Put that connection string into:

- `POSTGRES_URL`

### 4. Add your DeepSeek key

Put your DeepSeek API key into:

- `DEEPSEEK_API_KEY`

### 5. Deploy

Once the environment variables are added, deploy the project.

You usually do not need to manually fill in build commands if Vercel reads the included `vercel.json`.

## What happens after deployment

When the site is live, users can:

1. open the app
2. upload a PDF
3. wait for it to process
4. ask questions in the chat box
5. view usage stats in the insights tab

## How to use the app

### Upload a PDF

Click the upload area and choose a PDF from your computer.

Then click the upload button. The app will read the file and prepare it for question answering.

### Ask questions

After the PDF finishes uploading:

- type a question in the chat box
- press send

Example questions:

- `What is this document about?`
- `Summarize the main points`
- `What does it say about pricing?`
- `Does it mention deadlines?`

### Read the answer

The app gives:

- an answer
- the source text chunks it used

If the answer is not in the PDF, the app is supposed to say so.

### View insights

The insights tab shows:

- total questions asked
- most repeated questions
- questions grouped by day

## If something goes wrong

### Problem: upload works but questions fail

Check:

- `DEEPSEEK_API_KEY` is correct
- `POSTGRES_URL` is correct
- the PDF actually contains readable text

### Problem: deployment fails on Vercel

Check:

- the repo was imported correctly
- environment variables were added
- Vercel Postgres is connected
- the project is using the repo root and not just a subfolder

### Problem: the app opens but gives no useful answers

Possible reasons:

- the PDF has little or no readable text
- the PDF is mostly scanned images
- the answer is genuinely not present in the document

## Good PDFs for this app

Best results usually come from:

- reports
- contracts
- manuals
- notes
- articles
- policy documents

Harder PDFs include:

- scanned images with no selectable text
- handwritten pages
- very messy layouts

## In one sentence

Upload a PDF, ask questions, and SmartDoc AI answers using only the content from that document.
