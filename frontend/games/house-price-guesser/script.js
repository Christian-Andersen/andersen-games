const state = {
  mode: 'select',
  playingMode: 'daily',
  houses: [],
  currentHouseIndex: 0,
  currentImageIndex: 0,
  guesses: [],
  gameState: 'playing',
  guessInput: '',
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(value)
}

function getImageUrl(house, imagePath) {
  if (!imagePath) return ''
  if (imagePath.startsWith('http')) return imagePath
  // Photos live in a shared content-addressed pool, so entries carry their shard.
  return `./images/${imagePath}`
}

function parseSoldDate(soldDate) {
  const [year, month, day] = String(soldDate).split('-').map(Number)
  return new Date(year, month - 1, day)
}

function daysSinceEpoch(date) {
  return Math.floor(new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime() / 86400000)
}

function getHouseForDaily() {
  const count = state.houses.length
  if (count === 0) return 0
  // Houses are sorted newest first, so today is the most recent sale and each
  // following day walks one further back through the list, wrapping at the oldest.
  const offset = daysSinceEpoch(new Date()) - daysSinceEpoch(parseSoldDate(state.houses[0].soldDate))
  return ((offset % count) + count) % count
}

function startGame() {
  state.currentImageIndex = 0
  state.guesses = []
  state.guessInput = ''
  state.gameState = 'playing'
}

function renderSelect() {
  return `
    <div class="flex flex-1 flex-col items-center justify-center">
      <h2 class="mb-8 bg-gradient-to-r from-emerald-500 to-slate-500 bg-clip-text text-center text-5xl font-black text-transparent">
        House Price Guesser
      </h2>
      <div class="flex flex-wrap justify-center gap-5">
        <button onclick="selectDaily()" class="flex w-72 flex-col items-center rounded-2xl border-2 border-neutral-600 bg-neutral-800 px-8 py-8 text-white transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500">
          <span class="mb-2 text-5xl">📅</span>
          <span class="text-2xl font-extrabold">Daily Challenge</span>
        </button>
        <button onclick="selectArchive()" class="flex w-72 flex-col items-center rounded-2xl border-2 border-neutral-600 bg-neutral-800 px-8 py-8 text-white transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500">
          <span class="mb-2 text-5xl">🗄️</span>
          <span class="text-2xl font-extrabold">Archive</span>
        </button>
      </div>
    </div>
  `
}

function renderArchiveList() {
  const houses = state.houses
  return `
    <div class="flex flex-1 flex-col overflow-hidden p-5">
      <div class="mb-5 flex flex-shrink-0 items-center gap-5">
        <button onclick="setMode('select')" class="cursor-pointer rounded-lg bg-neutral-700 px-4 py-2 text-sm text-white">&larr; Back</button>
        <h2 class="m-0 text-2xl font-bold text-white">Archive</h2>
      </div>
      <div class="grid flex-1 auto-rows-[240px] gap-5 overflow-y-auto" style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))">
        ${houses.map((house, i) => `
          <div onclick="selectHouse(${i})" class="flex cursor-pointer flex-col overflow-hidden rounded-xl border border-neutral-700 bg-neutral-800 transition-all duration-200 hover:-translate-y-1 hover:border-emerald-500">
            <img src="${getImageUrl(house, house.images[0])}" alt="${house.address}" class="h-[150px] w-full flex-shrink-0 object-cover" loading="lazy" />
            <div class="flex flex-col justify-center px-3 py-3">
              <h4 class="m-0 mb-1 line-clamp-2 text-base leading-tight text-white">${house.address}</h4>
              <p class="m-0 text-xs text-neutral-500">${house.type} &bull; ${house.bedrooms} Bed</p>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `
}

function renderPlaying() {
  const house = state.houses[state.currentHouseIndex]
  if (!house) return ''

  const currentImage = house.images[state.currentImageIndex]
  const totalImages = house.images.length

  return `
    <div class="flex h-full flex-col overflow-hidden">
      <div class="game-header flex h-[50px] flex-shrink-0 items-center border-b border-neutral-700 bg-neutral-900 px-4">
        <button onclick="backFromPlaying()" class="cursor-pointer rounded-md bg-neutral-700 px-3 py-1.5 text-sm text-white">&larr; ${state.playingMode === 'daily' ? 'Menu' : 'Archive'}</button>
        <div class="flex-1 text-center text-sm font-bold uppercase tracking-wider text-emerald-500">${state.playingMode === 'daily' ? 'Daily Challenge' : 'Archive'}</div>
      </div>
      <div class="flex flex-1 flex-col overflow-hidden md:flex-row">
        <div class="flex flex-1 flex-col border-b border-neutral-700 bg-black md:border-b-0 md:flex-[1.4] md:border-r">
          <div class="relative flex min-h-0 flex-1">
            <img src="${getImageUrl(house, currentImage)}" alt="Property" class="h-full w-full object-contain" />
            <button onclick="prevImage()" class="absolute left-0 top-1/2 z-10 flex h-[70px] w-[50px] -translate-y-1/2 cursor-pointer items-center justify-center border-none bg-black/60 text-white transition-colors hover:bg-emerald-500 rounded-r-xl">&lsaquo;</button>
            <button onclick="nextImage()" class="absolute right-0 top-1/2 z-10 flex h-[70px] w-[50px] -translate-y-1/2 cursor-pointer items-center justify-center border-none bg-black/60 text-white transition-colors hover:bg-emerald-500 rounded-l-xl">&rsaquo;</button>
            <div class="absolute bottom-5 right-5 z-10 rounded-full bg-black/70 px-3 py-1 text-sm">${state.currentImageIndex + 1} / ${totalImages}</div>
          </div>
          <div class="hidden flex-shrink-0 bg-neutral-900 px-6 py-4 md:block">
            <h2 class="m-0 text-lg font-bold text-white md:text-2xl">${house.address}</h2>
          </div>
        </div>
        <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-neutral-800">
          <div class="flex-1 overflow-y-auto p-6">
            <div class="mb-6 md:hidden">
              <h2 class="m-0 text-lg font-bold text-white">${house.address}</h2>
            </div>
            <div class="mb-6 rounded-xl border border-neutral-700 bg-neutral-700/50 p-5">
              ${renderStats(house)}
              <div class="border-t border-neutral-600 pt-4 text-sm text-neutral-300">
                <div><span class="font-semibold text-neutral-500">Land Size:</span> ${house.landSize}m&sup2;</div>
                <div><span class="font-semibold text-neutral-500">Type:</span> ${house.type}</div>
                <div><span class="font-semibold text-neutral-500">Sold Date:</span> ${house.soldDate}</div>
                ${house.saleMethod ? `<div><span class="font-semibold text-neutral-500">Sold:</span> ${house.saleMethod}</div>` : ''}
                ${renderListingLink(house)}
              </div>
            </div>
            ${state.gameState === 'playing' ? renderGuessInput() : renderResult()}
            ${state.guesses.length > 0 ? renderHistory() : ''}
            ${renderDescription(house)}
          </div>
        </div>
      </div>
    </div>
  `
}

function renderStats(house) {
  const stats = [
    { icon: '🛏️', value: house.bedrooms, label: 'Bed' },
    { icon: '🛁', value: house.bathrooms, label: 'Bath' },
    { icon: '🚗', value: house.carSpaces, label: 'Car' },
  ]
  // Building size is only known for listings we could read a detail page for.
  if (house.buildingSize) stats.push({ icon: '🏠', value: `${house.buildingSize}m²`, label: 'Build' })

  return `
    <div class="mb-4 grid gap-2.5" style="grid-template-columns: repeat(${stats.length}, minmax(0, 1fr))">
      ${stats.map((stat) => `
        <div class="flex flex-col items-center gap-1 text-center">
          <span class="text-lg">${stat.icon}</span>
          <div><span class="block text-base font-extrabold text-white">${stat.value}</span><span class="block text-xs uppercase text-neutral-500">${stat.label}</span></div>
        </div>
      `).join('')}
    </div>
  `
}

function renderListingLink(house) {
  if (!house.listingUrl) return ''
  return `<div><span class="font-semibold text-neutral-500">Source:</span> <a href="${house.listingUrl}" target="_blank" rel="noopener noreferrer" class="cursor-pointer text-emerald-500 underline decoration-dotted underline-offset-2 hover:text-emerald-400">View on domain.com.au &nearr;</a></div>`
}

function renderDescription(house) {
  const text = String(house.description || '').replace(/<br\s*\/?>/gi, '\n').trim()
  if (!text) return ''
  return `
    <div class="mb-8">
      <h3 class="mb-3 text-xs font-bold uppercase tracking-wider text-emerald-500">Description</h3>
      <p class="whitespace-pre-line leading-relaxed text-neutral-300">${text}</p>
    </div>
  `
}

function renderGuessInput() {
  return `
    <div class="mb-6">
      <div class="flex items-center gap-0 rounded-xl border-2 border-neutral-600 bg-neutral-800 p-1.5">
        <span class="px-4 text-2xl font-extrabold text-neutral-500">$</span>
        <input
          id="guess-input"
          type="number"
          placeholder="Amount"
          value="${state.guessInput}"
          oninput="updateGuessInput(this)"
          onkeydown="if(event.key==='Enter')submitGuess()"
          class="min-w-0 flex-1 border-none bg-transparent text-2xl font-extrabold text-white outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        <button onclick="submitGuess()" class="cursor-pointer rounded-lg border-none bg-emerald-600 px-6 py-2 font-extrabold text-white transition-colors hover:bg-emerald-500">GUESS</button>
      </div>
    </div>
  `
}

function renderResult() {
  const house = state.houses[state.currentHouseIndex]
  return `
    <div class="mb-6 rounded-2xl border-2 border-emerald-500 bg-emerald-900/30 p-6 text-center">
      <div class="text-5xl">🎉</div>
      <h3 class="text-2xl font-black text-emerald-400">CORRECT!</h3>
      <p class="text-2xl font-extrabold text-white">${formatCurrency(house.price)}</p>
      <div class="mt-2 text-sm text-neutral-400">Solved in ${state.guesses.length} attempts</div>
    </div>
  `
}

function renderHistory() {
  return `
    <div class="mb-6">
      <h4 class="mb-4 text-xs font-bold tracking-widest text-neutral-500">HISTORY</h4>
      ${state.guesses.map((g) => {
        const isHigher = g.hint.includes('Higher')
        const isLower = g.hint.includes('Lower')
        return `
          <div class="mb-2 flex items-center justify-between rounded-xl border border-neutral-700 bg-neutral-700/50 px-5 py-3 font-mono text-lg">
            <span>${formatCurrency(g.value)}</span>
            <span class="${isHigher ? 'text-emerald-400' : ''} ${isLower ? 'text-red-400' : ''} font-bold">${g.hint}</span>
          </div>
        `
      }).join('')}
    </div>
  `
}

function render() {
  const app = document.getElementById('app')
  let html
  switch (state.mode) {
    case 'select': html = renderSelect(); break
    case 'archive-list': html = renderArchiveList(); break
    case 'playing': html = renderPlaying(); break
    default: html = renderSelect()
  }
  app.innerHTML = html
  if (state.mode === 'playing' && state.gameState === 'playing') {
    const input = document.getElementById('guess-input')
    if (input) {
      input.focus()
      input.value = state.guessInput
      input.setSelectionRange(input.value.length, input.value.length)
    }
  }
}

function setMode(mode) {
  state.mode = mode
  render()
}

function selectDaily() {
  state.playingMode = 'daily'
  state.currentHouseIndex = getHouseForDaily()
  startGame()
  setMode('playing')
}

function selectArchive() {
  setMode('archive-list')
}

function selectHouse(index) {
  state.playingMode = 'archive'
  state.currentHouseIndex = index
  startGame()
  setMode('playing')
}

function backFromPlaying() {
  setMode(state.playingMode === 'daily' ? 'select' : 'archive-list')
}

function updateGuessInput(el) {
  state.guessInput = el.value
}

function submitGuess() {
  if (!state.guessInput || state.gameState !== 'playing') return
  const guess = Number(state.guessInput)
  if (isNaN(guess)) return
  const house = state.houses[state.currentHouseIndex]
  const target = house.price
  const margin = target * 0.05
  const won = Math.abs(guess - target) <= margin
  const hint = won ? 'Correct ✓' : guess < target ? 'Higher ↑' : 'Lower ↓'
  state.guesses.unshift({ value: guess, hint })
  if (won) {
    state.gameState = 'won'
  }
  state.guessInput = ''
  render()
}

function nextImage() {
  const house = state.houses[state.currentHouseIndex]
  if (!house) return
  state.currentImageIndex = (state.currentImageIndex + 1) % house.images.length
  render()
}

function prevImage() {
  const house = state.houses[state.currentHouseIndex]
  if (!house) return
  state.currentImageIndex = (state.currentImageIndex - 1 + house.images.length) % house.images.length
  render()
}

;(async function init() {
  const res = await fetch('./data.json')
  const houses = await res.json()
  // getHouseForDaily walks the list backwards from the newest sale, so order matters.
  houses.sort((a, b) => parseSoldDate(b.soldDate) - parseSoldDate(a.soldDate))
  state.houses = houses
  render()
})()
