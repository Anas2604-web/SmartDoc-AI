<script setup>
import { computed, onMounted, ref } from 'vue'
import { askQuestion, fetchInsights, uploadPdf } from './lib/api'

const activeTab = ref('chat')
const selectedFile = ref(null)
const uploadState = ref({ loading: false, error: '', success: '' })
const askState = ref({ loading: false, error: '' })
const documentId = ref('')
const pdfName = ref('')
const chunkCount = ref(0)
const question = ref('')
const chatMessages = ref([
  {
    role: 'assistant',
    content: 'Upload a PDF and ask questions about it. I will answer only from the retrieved document context.',
    sources: []
  }
])
const insights = ref({
  total_questions: 0,
  most_asked_questions: [],
  questions_per_day: [],
  latest_pdf_name: null
})

const hasDocument = computed(() => Boolean(documentId.value))

function onFileChange(event) {
  const [file] = event.target.files || []
  selectedFile.value = file || null
  uploadState.value = { loading: false, error: '', success: '' }
}

async function handleUpload() {
  if (!selectedFile.value) {
    uploadState.value = { loading: false, error: 'Choose a PDF before uploading.', success: '' }
    return
  }

  uploadState.value = { loading: true, error: '', success: '' }
  try {
    const response = await uploadPdf(selectedFile.value)
    documentId.value = response.document_id
    pdfName.value = response.pdf_name
    chunkCount.value = response.chunk_count
    uploadState.value = {
      loading: false,
      error: '',
      success: `${response.pdf_name} indexed successfully with ${response.chunk_count} chunks.`
    }
    activeTab.value = 'chat'
  } catch (error) {
    uploadState.value = { loading: false, error: error.message, success: '' }
  }
}

async function handleAsk() {
  const trimmed = question.value.trim()
  if (!trimmed || !documentId.value) {
    return
  }

  askState.value = { loading: true, error: '' }
  chatMessages.value.push({ role: 'user', content: trimmed, sources: [] })
  question.value = ''

  try {
    const response = await askQuestion({
      document_id: documentId.value,
      question: trimmed
    })

    chatMessages.value.push({
      role: 'assistant',
      content: response.answer,
      sources: response.sources || []
    })
    await loadInsights()
  } catch (error) {
    askState.value = { loading: false, error: error.message }
    chatMessages.value.push({
      role: 'assistant',
      content: `Error: ${error.message}`,
      sources: []
    })
    return
  }

  askState.value = { loading: false, error: '' }
}

async function loadInsights() {
  try {
    insights.value = await fetchInsights()
  } catch (error) {
    insights.value = {
      total_questions: 0,
      most_asked_questions: [],
      questions_per_day: [],
      latest_pdf_name: null,
      error: error.message
    }
  }
}

function formatDay(day) {
  return new Date(day).toLocaleDateString()
}

onMounted(loadInsights)
</script>

<template>
  <div class="min-h-screen bg-slate-950">
    <div class="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
      <header class="panel overflow-hidden">
        <div class="bg-gradient-to-r from-brand-700 via-brand-500 to-cyan-500 p-8">
          <p class="text-sm font-medium uppercase tracking-[0.25em] text-white/80">RAG document assistant</p>
          <h1 class="mt-3 text-4xl font-bold text-white">SmartDoc AI</h1>
          <p class="mt-4 max-w-3xl text-sm text-white/85 sm:text-base">
            Upload a PDF, build local embeddings with FAISS, ask grounded questions, and track usage insights from Postgres.
          </p>
        </div>
      </header>

      <section class="grid gap-6 lg:grid-cols-[360px,1fr]">
        <aside class="panel p-5">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">Document setup</h2>
            <span class="rounded-full bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-100">
              {{ hasDocument ? 'Ready' : 'Waiting' }}
            </span>
          </div>

          <div class="mt-5 space-y-4">
            <label class="block">
              <span class="mb-2 block text-sm font-medium text-slate-200">PDF file</span>
              <input
                class="input file:mr-4 file:rounded-lg file:border-0 file:bg-brand-500 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-700"
                type="file"
                accept="application/pdf"
                @change="onFileChange"
              />
            </label>

            <button class="button-primary w-full" :disabled="uploadState.loading" @click="handleUpload">
              {{ uploadState.loading ? 'Indexing PDF...' : 'Upload and index' }}
            </button>

            <div class="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
              <p class="font-medium text-white">Current document</p>
              <p class="mt-2">{{ pdfName || 'No PDF uploaded yet.' }}</p>
              <p v-if="chunkCount" class="mt-1 text-slate-400">{{ chunkCount }} chunks stored in FAISS.</p>
            </div>

            <p v-if="uploadState.success" class="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {{ uploadState.success }}
            </p>
            <p v-if="uploadState.error" class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {{ uploadState.error }}
            </p>
          </div>
        </aside>

        <main class="space-y-6">
          <div class="flex gap-3">
            <button
              class="button-secondary"
              :class="activeTab === 'chat' ? 'border-brand-500 bg-brand-500/10 text-brand-100' : ''"
              @click="activeTab = 'chat'"
            >
              Chat
            </button>
            <button
              class="button-secondary"
              :class="activeTab === 'insights' ? 'border-brand-500 bg-brand-500/10 text-brand-100' : ''"
              @click="activeTab = 'insights'"
            >
              Insights
            </button>
          </div>

          <section v-if="activeTab === 'chat'" class="panel flex min-h-[620px] flex-col">
            <div class="border-b border-slate-800 px-6 py-5">
              <h2 class="text-lg font-semibold text-white">Document Q&amp;A</h2>
              <p class="mt-1 text-sm text-slate-400">
                Answers are generated from the top retrieved chunks only.
              </p>
            </div>

            <div class="flex-1 space-y-4 overflow-y-auto px-6 py-5">
              <article
                v-for="(message, index) in chatMessages"
                :key="index"
                class="rounded-2xl border p-4"
                :class="message.role === 'assistant'
                  ? 'border-slate-800 bg-slate-900/60'
                  : 'ml-auto border-brand-500/20 bg-brand-500/10'"
              >
                <div class="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.2em]">
                  <span :class="message.role === 'assistant' ? 'text-slate-400' : 'text-brand-100'">
                    {{ message.role }}
                  </span>
                </div>
                <p class="whitespace-pre-wrap text-sm leading-7 text-slate-100">{{ message.content }}</p>

                <div v-if="message.sources?.length" class="mt-4 space-y-3">
                  <div
                    v-for="source in message.sources"
                    :key="`${index}-${source.rank}`"
                    class="rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                  >
                    <div class="flex items-center justify-between text-xs text-slate-400">
                      <span>Source {{ source.rank }}</span>
                      <span>Score {{ source.score.toFixed(3) }}</span>
                    </div>
                    <p class="mt-2 text-sm text-slate-300">{{ source.content }}</p>
                  </div>
                </div>
              </article>
            </div>

            <div class="border-t border-slate-800 px-6 py-5">
              <label class="mb-3 block text-sm font-medium text-slate-200">Ask about the uploaded PDF</label>
              <div class="flex flex-col gap-3 sm:flex-row">
                <input
                  v-model="question"
                  class="input flex-1"
                  placeholder="What does this document say about...?"
                  :disabled="!hasDocument || askState.loading"
                  @keyup.enter="handleAsk"
                />
                <button
                  class="button-primary sm:w-36"
                  :disabled="!hasDocument || askState.loading || !question.trim()"
                  @click="handleAsk"
                >
                  {{ askState.loading ? 'Thinking...' : 'Send' }}
                </button>
              </div>
              <p v-if="askState.error" class="mt-3 text-sm text-rose-300">{{ askState.error }}</p>
            </div>
          </section>

          <section v-else class="panel p-6">
            <div class="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 class="text-lg font-semibold text-white">Usage insights</h2>
                <p class="mt-1 text-sm text-slate-400">SQL-backed analytics from the `usage_log` table.</p>
              </div>
              <button class="button-secondary" @click="loadInsights">Refresh</button>
            </div>

            <div class="mt-6 grid gap-4 md:grid-cols-3">
              <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <p class="text-sm text-slate-400">Total questions</p>
                <p class="mt-2 text-3xl font-bold text-white">{{ insights.total_questions }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <p class="text-sm text-slate-400">Latest PDF</p>
                <p class="mt-2 text-lg font-semibold text-white">{{ insights.latest_pdf_name || 'No activity yet' }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <p class="text-sm text-slate-400">Tracked queries</p>
                <p class="mt-2 text-lg font-semibold text-white">{{ insights.most_asked_questions.length }}</p>
              </div>
            </div>

            <div class="mt-6 grid gap-6 lg:grid-cols-2">
              <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <h3 class="text-base font-semibold text-white">Most asked questions</h3>
                <div class="mt-4 overflow-hidden rounded-xl border border-slate-800">
                  <table class="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead class="bg-slate-900">
                      <tr>
                        <th class="px-4 py-3 font-medium text-slate-300">Question</th>
                        <th class="px-4 py-3 font-medium text-slate-300">Count</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                      <tr v-for="item in insights.most_asked_questions" :key="item.question">
                        <td class="px-4 py-3 text-slate-200">{{ item.question }}</td>
                        <td class="px-4 py-3 text-slate-400">{{ item.count }}</td>
                      </tr>
                      <tr v-if="!insights.most_asked_questions.length">
                        <td colspan="2" class="px-4 py-6 text-center text-slate-500">No questions logged yet.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
                <h3 class="text-base font-semibold text-white">Questions per day</h3>
                <div class="mt-4 overflow-hidden rounded-xl border border-slate-800">
                  <table class="min-w-full divide-y divide-slate-800 text-left text-sm">
                    <thead class="bg-slate-900">
                      <tr>
                        <th class="px-4 py-3 font-medium text-slate-300">Day</th>
                        <th class="px-4 py-3 font-medium text-slate-300">Count</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                      <tr v-for="item in insights.questions_per_day" :key="item.day">
                        <td class="px-4 py-3 text-slate-200">{{ formatDay(item.day) }}</td>
                        <td class="px-4 py-3 text-slate-400">{{ item.count }}</td>
                      </tr>
                      <tr v-if="!insights.questions_per_day.length">
                        <td colspan="2" class="px-4 py-6 text-center text-slate-500">No daily usage yet.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <p v-if="insights.error" class="mt-4 text-sm text-rose-300">{{ insights.error }}</p>
          </section>
        </main>
      </section>
    </div>
  </div>
</template>
