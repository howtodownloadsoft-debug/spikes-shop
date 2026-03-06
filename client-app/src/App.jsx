import { useEffect, useState, useRef } from 'react'
import { supabase } from './supabaseClient'
import ProductCard from './components/ProductCard'

const tg = window.Telegram?.WebApp
function haptic(type = 'light') {
  try { tg?.HapticFeedback?.impactOccurred(type) } catch(e) {}
}

const MAIN_CATS = ['Все', 'Обувь', 'Одежда', 'Аксессуары']

const SUB_CATS = {
  'Обувь':      ['Все', 'Шиповки', 'Кроссовки'],
  'Одежда':     ['Все', 'Верх', 'Низ', 'Костюмы'],
  'Аксессуары': ['Все', 'Рюкзаки/Сумки', 'Носки', 'Разное'],
}

// ✅ ИЗМЕНЕНИЕ 1: убраны Кросс и Универсальные
const DISTANCES = ['Все', 'Спринт', 'Средние', 'Длинные', 'Прыжки', 'Метания']

const SHOE_SIZES    = ['36','37','37.5','38','38.5','39','40','40.5','41','42','42.5','43','44','44.5','45','46','47']
const CLOTHES_SIZES = ['XS','S','M','L','XL','XXL']

export default function App() {
  const [products, setProducts]       = useState([])
  const [loading, setLoading]         = useState(true)
  const [search, setSearch]           = useState('')
  const [debouncedSearch, setDebounced] = useState('')
  const [mainCat, setMainCat]         = useState('Все')
  const [subCat, setSubCat]           = useState('Все')
  const [distance, setDistance]       = useState('Все')
  const [selected, setSelected]       = useState(null)
  const [activeImg, setActiveImg]     = useState(0)
  const [cart, setCart]               = useState([])
  const [cartOpen, setCartOpen]       = useState(false)
  const [cartBounce, setCartBounce]   = useState(false)
  const [swipedItem, setSwipedItem]   = useState(null)

  const [selectedSize, setSelectedSize] = useState(null)
  const [orderName, setOrderName]       = useState('')
  const [orderPhone, setOrderPhone]     = useState('')
  const [orderAddress, setOrderAddress] = useState('')
  const [orderComment, setOrderComment] = useState('')
  const [orderSent, setOrderSent]       = useState(false)

  const touchStartX    = useRef(null)
  const cartSwipeStart = useRef(null)
  const savedScrollY   = useRef(0)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => { setSubCat('Все'); setDistance('Все') }, [mainCat])
  useEffect(() => { setDistance('Все') }, [subCat])
  useEffect(() => { fetchProducts() }, [mainCat, subCat, distance, debouncedSearch])

  useEffect(() => {
    if (selected) {
      setActiveImg(0)
      setSelectedSize(null)
      setOrderSent(false)
      setOrderName(''); setOrderPhone(''); setOrderAddress(''); setOrderComment('')
      window.scrollTo(0, 0)
      selected.images?.forEach(src => { const img = new Image(); img.src = src })
    }
  }, [selected])

  useEffect(() => {
    if (!tg?.MainButton) return
    const ready = selected && selectedSize && orderName.trim() && orderPhone.trim() && orderAddress.trim()
    if (ready && !orderSent) {
      tg.MainButton.setText(`Оформить заказ — ${selected.price_rub.toLocaleString('ru-RU')} ₽`)
      tg.MainButton.color = '#FF5A00'
      tg.MainButton.show()
      tg.MainButton.onClick(handleSubmitOrder)
    } else {
      tg.MainButton.hide()
      tg.MainButton.offClick(handleSubmitOrder)
    }
    return () => { tg.MainButton.hide(); tg.MainButton.offClick(handleSubmitOrder) }
  }, [selected, selectedSize, orderName, orderPhone, orderAddress, orderSent])

  async function fetchProducts() {
    setLoading(true)
    let q = supabase.from('products_v2').select('*').order('price_rub', { ascending: true }).limit(100)
    if (mainCat !== 'Все') q = q.eq('main_category', mainCat)
    if (subCat !== 'Все')  q = q.eq('sub_category', subCat)
    // ✅ ИЗМЕНЕНИЕ 2: правильный фильтр для массива дистанций
    if (distance !== 'Все') q = q.contains('attributes', { distance: [distance] })
    if (debouncedSearch.trim()) q = q.ilike('name', `%${debouncedSearch.trim()}%`)
    const { data, error } = await q
    if (!error) setProducts(data || [])
    setLoading(false)
  }

  function handleSubmitOrder() {
    if (!selected || !selectedSize || !orderName.trim() || !orderPhone.trim() || !orderAddress.trim()) return
    haptic('heavy')
    const payload = JSON.stringify({
      product: selected.name, brand: selected.brand,
      size: selectedSize, price: `${selected.price_rub.toLocaleString('ru-RU')} ₽`,
      name: orderName, phone: orderPhone,
      address: orderAddress, comment: orderComment,
    })
    tg?.sendData(payload)
    setOrderSent(true)
    tg?.MainButton.hide()
  }

  function getSizes(product) {
    if (product?.main_category === 'Одежда')     return CLOTHES_SIZES
    if (product?.main_category === 'Аксессуары') return ['One Size']
    return SHOE_SIZES
  }

  function openProduct(p) { savedScrollY.current = window.scrollY; haptic('medium'); setSelected(p) }
  function closeProduct()  { setSelected(null); requestAnimationFrame(() => window.scrollTo(0, savedScrollY.current)) }
  function openCart()      { savedScrollY.current = window.scrollY; haptic(); setCartOpen(true); window.scrollTo(0, 0) }
  function closeCart()     { setCartOpen(false); setSwipedItem(null); requestAnimationFrame(() => window.scrollTo(0, savedScrollY.current)) }

  function addToCart(product) {
    haptic('medium')
    setCart(prev => {
      const ex = prev.find(i => i.product.id === product.id)
      return ex ? prev.map(i => i.product.id === product.id ? { ...i, quantity: i.quantity + 1 } : i)
                : [...prev, { product, quantity: 1 }]
    })
    setCartBounce(true); setTimeout(() => setCartBounce(false), 500)
  }

  function removeFromCart(id) { haptic('light'); setCart(p => p.filter(i => i.product.id !== id)); setSwipedItem(null) }
  function totalItems() { return cart.reduce((s, i) => s + i.quantity, 0) }
  function totalPrice() { return cart.reduce((s, i) => s + i.product.price_rub * i.quantity, 0) }

  function handleTouchStart(e) { touchStartX.current = e.touches[0].clientX }
  function handleTouchEnd(e, len) {
    if (touchStartX.current === null) return
    const diff = touchStartX.current - e.changedTouches[0].clientX
    if (Math.abs(diff) > 50) diff > 0 ? setActiveImg(i => Math.min(i+1, len-1)) : setActiveImg(i => Math.max(i-1, 0))
    touchStartX.current = null
  }
  function handleCartSwipeStart(e) { cartSwipeStart.current = e.touches[0].clientX }
  function handleCartSwipeEnd(e, id) {
    if (cartSwipeStart.current === null) return
    const diff = cartSwipeStart.current - e.changedTouches[0].clientX
    if (diff > 55) { haptic(); setSwipedItem(id) } else if (diff < -20) setSwipedItem(null)
    cartSwipeStart.current = null
  }

  function CartBtn() {
    return (
      <button onClick={openCart} className="relative w-10 h-10 bg-white/8 border border-white/5 rounded-full flex items-center justify-center active:scale-90 transition-transform">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 01-8 0" strokeLinecap="round"/>
        </svg>
        {totalItems() > 0 && (
          <span className={`absolute -top-1.5 -right-1.5 bg-[#FF5A00] text-white text-[10px] font-bold px-1.5 rounded-full min-w-[18px] text-center leading-none py-[3px] ${cartBounce ? 'cart-pop' : ''}`}>
            {totalItems()}
          </span>
        )}
      </button>
    )
  }

  // ─── КОРЗИНА ──────────────────────────────────────────────────────────────────
  if (cartOpen) return (
    <div className="min-h-screen bg-[#0F1115] text-white font-sans pb-10 page-enter">
      <div className="fixed top-0 w-full bg-[#0F1115]/90 backdrop-blur-md z-30 px-4 py-4 flex items-center gap-3 border-b border-white/5">
        <button onClick={closeCart} className="w-10 h-10 bg-white/8 rounded-full flex items-center justify-center active:scale-90 transition-transform border border-white/5">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <h1 className="text-lg font-bold">Корзина</h1>
        {totalItems() > 0 && <span className="ml-auto text-sm text-zinc-500">{totalItems()} шт.</span>}
      </div>

      <div className="pt-20 px-4">
        {cart.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-zinc-600">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" strokeLinecap="round" strokeLinejoin="round"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0" strokeLinecap="round"/>
            </svg>
            <p className="text-sm">Корзина пуста</p>
          </div>
        ) : (
          <>
            <p className="text-xs text-zinc-600 text-center mb-3">← свайп влево для удаления</p>
            <div className="flex flex-col gap-3 mb-6">
              {cart.map(({ product, quantity }) => (
                <div key={product.id} className="relative overflow-hidden rounded-2xl"
                  onTouchStart={handleCartSwipeStart} onTouchEnd={(e) => handleCartSwipeEnd(e, product.id)}>
                  <div className="absolute inset-y-0 right-0 w-20 bg-red-500 flex items-center justify-center rounded-r-2xl">
                    <button onPointerDown={(e) => { e.stopPropagation(); removeFromCart(product.id) }} className="active:scale-90 transition-transform">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" strokeLinecap="round"/>
                        <path d="M10 11v6M14 11v6" strokeLinecap="round"/>
                      </svg>
                    </button>
                  </div>
                  <div className="relative bg-[#1C1E24] border border-white/5 rounded-2xl p-3 flex items-center gap-3 transition-transform duration-200 ease-out"
                    style={{ transform: swipedItem === product.id ? 'translateX(-80px)' : 'translateX(0)' }}>
                    <div className="w-16 h-16 bg-[#EBEBED] rounded-xl flex-shrink-0">
                      <img src={product.images?.[0]} alt={product.name} loading="lazy" className="w-full h-full object-contain mix-blend-multiply p-1"/>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#888]">{product.brand}</p>
                      <p className="text-sm font-semibold leading-tight line-clamp-2 mt-0.5">{product.name}</p>
                      <p className="text-sm font-bold mt-1.5">
                        {(product.price_rub * quantity).toLocaleString('ru-RU')} ₽
                        {quantity > 1 && <span className="text-xs text-zinc-500 font-normal ml-2">x{quantity}</span>}
                      </p>
                    </div>
                    <button onClick={() => removeFromCart(product.id)} className="w-8 h-8 bg-white/8 border border-white/5 rounded-full flex items-center justify-center flex-shrink-0 active:scale-90 transition-transform">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="bg-[#1C1E24] border border-white/5 rounded-2xl p-5 mb-6">
              <div className="flex justify-between text-sm text-zinc-500 mb-2"><span>Товаров</span><span>{totalItems()} шт.</span></div>
              <div className="flex justify-between font-bold text-lg"><span>Итого</span><span className="text-[#FF5A00]">{totalPrice().toLocaleString('ru-RU')} ₽</span></div>
            </div>
            <button onClick={() => haptic('heavy')} className="w-full bg-[#FF5A00] text-white font-bold py-4 rounded-2xl active:scale-[0.97] transition-transform text-base shadow-lg shadow-[#FF5A00]/25">
              Оформить заказ
            </button>
          </>
        )}
      </div>
    </div>
  )

  // ─── КАРТОЧКА ТОВАРА ────────────────────────────────────────────────────────
  if (selected) {
    const images  = selected.images || []
    const sizes   = getSizes(selected)
    const distVal = selected.attributes?.distance
    const isFormReady = orderName.trim() && orderPhone.trim() && orderAddress.trim()

    return (
      <div className="min-h-screen bg-[#0F1115] text-white font-sans page-enter">
        <div className="fixed top-0 w-full bg-[#0F1115]/85 backdrop-blur-md z-30 px-4 py-4 flex items-center justify-between border-b border-white/5">
          <button onClick={closeProduct} className="w-10 h-10 bg-white/8 border border-white/5 rounded-full flex items-center justify-center active:scale-90 transition-transform">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <CartBtn />
        </div>

        <div className="pt-[72px] px-4 pb-3 select-none" onTouchStart={handleTouchStart} onTouchEnd={(e) => handleTouchEnd(e, images.length)}>
          <div className="relative bg-[#EBEBED] rounded-3xl overflow-hidden" style={{ aspectRatio: '4/3' }}>
            <img key={activeImg} src={images[activeImg]} alt={selected.name} loading="lazy"
              className="w-full h-full object-contain p-4 mix-blend-multiply img-fadein"/>
            {images.length > 1 && (
              <>
                <button onClick={() => setActiveImg(i => Math.max(i-1, 0))}
                  className={`absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/8 text-black rounded-full flex items-center justify-center active:scale-90 transition-all ${activeImg === 0 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </button>
                <button onClick={() => setActiveImg(i => Math.min(i+1, images.length-1))}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/8 text-black rounded-full flex items-center justify-center active:scale-90 transition-all ${activeImg === images.length-1 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </button>
              </>
            )}
          </div>
        </div>

        {images.length > 1 && (
          <div className="flex gap-2 justify-center pb-4">
            {images.map((_, i) => (
              <button key={i} onClick={() => setActiveImg(i)}
                className={`h-1.5 rounded-full transition-all duration-300 ${i === activeImg ? 'bg-[#FF5A00] w-6' : 'bg-white/20 w-1.5'}`}/>
            ))}
          </div>
        )}

        <div className="px-5 pt-1 pb-36">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <p className="text-[#888] text-xs font-semibold tracking-widest uppercase">{selected.brand}</p>
              <h1 className="text-2xl font-bold leading-tight text-white mt-1">{selected.name}</h1>
            </div>
            {/* ✅ ИЗМЕНЕНИЕ 3: правильный рендер массива дистанций */}
            {distVal && distVal.length > 0 && (
              <span className="mt-2 flex-shrink-0 bg-[#FF5A00]/15 border border-[#FF5A00]/30 text-[#FF5A00] text-xs font-bold px-3 py-1.5 rounded-full">
                {Array.isArray(distVal) ? distVal.join(' · ') : distVal}
              </span>
            )}
          </div>

          <div className="flex items-end gap-3 mt-4 mb-5">
            <span className="text-3xl font-black text-white tracking-tight">{selected.price_rub.toLocaleString('ru-RU')} ₽</span>
            {selected.original_price_eur && (
              <span className="text-base text-zinc-500 line-through mb-0.5">
                {Math.round(selected.original_price_eur * (selected.price_rub / selected.price_eur)).toLocaleString('ru-RU')} ₽
              </span>
            )}
          </div>

          <div className="bg-[#1C1E24] border border-white/5 rounded-2xl p-5 mb-6">
            <p className="text-zinc-400 text-sm leading-relaxed whitespace-pre-line">{selected.description}</p>
          </div>

          <div className="mb-5">
            <p className="text-sm font-semibold mb-3 text-white">
              {selected.main_category === 'Одежда' ? 'Выберите размер' : 'Выберите размер (EU)'}
              {selectedSize && <span className="text-[#FF5A00] ml-2">— {selectedSize}</span>}
            </p>
            <div className="flex flex-wrap gap-2">
              {sizes.map(size => (
                <button key={size} onClick={() => { haptic(); setSelectedSize(size === selectedSize ? null : size) }}
                  className={`min-w-[50px] px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 active:scale-90 ${
                    selectedSize === size
                      ? 'bg-[#FF5A00] text-white shadow-lg shadow-[#FF5A00]/30'
                      : 'bg-white/8 border border-white/10 text-zinc-300'
                  }`}>
                  {size}
                </button>
              ))}
            </div>
          </div>

          {selectedSize && !orderSent && (
            <div className="bg-[#1C1E24] border border-white/5 rounded-2xl p-5 space-y-3">
              <p className="text-sm font-bold text-white mb-1">Оформление заказа</p>
              <input type="text" placeholder="Ваше имя *" value={orderName} onChange={e => setOrderName(e.target.value)}
                className="w-full bg-[#0F1115] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#FF5A00]/50 transition-colors"/>
              <input type="tel" placeholder="Телефон *" value={orderPhone} onChange={e => setOrderPhone(e.target.value)}
                className="w-full bg-[#0F1115] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#FF5A00]/50 transition-colors"/>
              <input type="text" placeholder="Адрес доставки *" value={orderAddress} onChange={e => setOrderAddress(e.target.value)}
                className="w-full bg-[#0F1115] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#FF5A00]/50 transition-colors"/>
              <textarea placeholder="Комментарий к заказу" value={orderComment} onChange={e => setOrderComment(e.target.value)} rows={2}
                className="w-full bg-[#0F1115] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-[#FF5A00]/50 transition-colors resize-none"/>
              {!tg && (
                <button onClick={handleSubmitOrder} disabled={!isFormReady}
                  className="w-full bg-[#FF5A00] disabled:bg-white/10 disabled:text-zinc-600 text-white font-bold py-4 rounded-2xl active:scale-[0.97] transition-all text-base shadow-lg shadow-[#FF5A00]/25">
                  Оформить заказ — {selected.price_rub.toLocaleString('ru-RU')} ₽
                </button>
              )}
            </div>
          )}

          {orderSent && (
            <div className="bg-[#1C1E24] border border-white/5 rounded-2xl p-8 text-center">
              <div className="text-5xl mb-4">✅</div>
              <p className="font-bold text-white text-xl mb-2">Заказ отправлен!</p>
              <p className="text-zinc-500 text-sm">Менеджер свяжется с вами в течение 15 минут</p>
            </div>
          )}
        </div>

        {!orderSent && (
          <div className="fixed bottom-0 left-0 right-0 px-4 pb-6 pt-3 bg-[#0F1115]/90 backdrop-blur-xl border-t border-white/5 z-30">
            {!selectedSize ? (
              <div className="text-center text-zinc-600 text-sm py-1">👆 Выберите размер для оформления заказа</div>
            ) : !isFormReady ? (
              <div className="text-center text-zinc-600 text-sm py-1">📝 Заполните все поля выше</div>
            ) : tg ? (
              <div className="text-center text-zinc-500 text-xs py-1">Нажмите кнопку <span className="text-[#FF5A00]">«Оформить заказ»</span> внизу экрана</div>
            ) : null}
          </div>
        )}
      </div>
    )
  }

  // ─── КАТАЛОГ ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0F1115] text-white pb-8 font-sans">
      <div className="sticky top-0 bg-[#0F1115]/95 backdrop-blur-md z-10 border-b border-white/5">
        <div className="px-4 pt-5 pb-3">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-black tracking-tight">Каталог</h1>
            <CartBtn />
          </div>

          <div className="relative mb-3">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" strokeLinecap="round"/>
            </svg>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Поиск по названию..." autoComplete="off"
              className="w-full bg-white/6 border border-white/8 rounded-xl pl-10 pr-10 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-white/20 transition-colors"/>
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 active:scale-90 transition-transform">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            )}
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar mb-2">
            {MAIN_CATS.map(cat => (
              <button key={cat} onClick={() => { haptic(); setMainCat(cat) }}
                className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-semibold transition-all duration-200 active:scale-95 ${
                  mainCat === cat
                    ? 'bg-[#FF5A00] text-white shadow-[0_0_14px_rgba(255,90,0,0.5)]'
                    : 'bg-white/7 text-zinc-400 border border-white/8'
                }`}>
                {cat}
              </button>
            ))}
          </div>

          {mainCat !== 'Все' && (
            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar mb-2">
              {SUB_CATS[mainCat].map(sub => (
                <button key={sub} onClick={() => { haptic(); setSubCat(sub) }}
                  className={`flex-shrink-0 px-3.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 active:scale-95 ${
                    subCat === sub ? 'bg-white text-black' : 'bg-white/7 text-zinc-500 border border-white/8'
                  }`}>
                  {sub}
                </button>
              ))}
            </div>
          )}

          {subCat === 'Шиповки' && (
            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
              {DISTANCES.map(d => (
                <button key={d} onClick={() => { haptic(); setDistance(d) }}
                  className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-all duration-200 active:scale-95 ${
                    distance === d
                      ? 'bg-[#FF5A00]/20 border border-[#FF5A00]/50 text-[#FF5A00]'
                      : 'bg-white/5 text-zinc-600 border border-white/5'
                  }`}>
                  {d}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="px-4 pt-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-[#1C1E24] rounded-2xl overflow-hidden border border-white/5">
                <div className="aspect-square skeleton-shimmer"/>
                <div className="p-3 space-y-2">
                  <div className="h-2.5 w-2/5 rounded skeleton-shimmer"/>
                  <div className="h-3 w-4/5 rounded skeleton-shimmer"/>
                  <div className="h-4 w-2/5 rounded skeleton-shimmer mt-1"/>
                </div>
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-56 gap-3 text-zinc-600">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35" strokeLinecap="round"/>
            </svg>
            <p className="text-sm">Товары не найдены</p>
            <button onClick={() => { setSearch(''); setMainCat('Все'); setSubCat('Все'); setDistance('Все') }}
              className="text-xs text-[#FF5A00] border border-[#FF5A00]/30 px-4 py-2 rounded-full active:scale-95 transition-transform">
              Сбросить фильтры
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {products.map((p, i) => (
              <div key={p.id} className="card-stagger" style={{ animationDelay: `${i * 0.04}s` }}>
                <ProductCard product={p} onClick={openProduct} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
