import { useEffect, useState, useRef } from 'react'
import { supabase } from './supabaseClient'
import ProductCard from './components/ProductCard'

const FILTERS = [
  { label: 'Все', value: null },
  { label: 'Спринт', value: 'Спринт' },
  { label: 'Средние', value: 'Средние дистанции' },
  { label: 'Длинные', value: 'Длинные дистанции' },
]

export default function App() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState(null)
  const [selected, setSelected] = useState(null)
  const [activeImg, setActiveImg] = useState(0)
  const [cart, setCart] = useState([])
  const [cartOpen, setCartOpen] = useState(false)
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [cartOpen])
  
  const [addedAnim, setAddedAnim] = useState(false)
  const touchStartX = useRef(null)

  useEffect(() => { fetchProducts() }, [filter])
  useEffect(() => {
    setActiveImg(0)
    window.scrollTo(0, 0)
    if (selected?.images) {
      selected.images.forEach(src => {
        const img = new Image()
        img.src = src
      })
    }
  }, [selected])
  

  async function fetchProducts() {
    setLoading(true)
    let query = supabase
      .from('products')
      .select('*')
      .order('price_rub', { ascending: true })
      .limit(20)
    if (filter) query = query.ilike('distance', `%${filter}%`)
    const { data, error } = await query
    if (!error) setProducts(data)
    setLoading(false)
  }

  function addToCart(product) {
    setCart(prev => {
      const existing = prev.find(i => i.product.id === product.id)
      if (existing) return prev.map(i => i.product.id === product.id ? { ...i, quantity: i.quantity + 1 } : i)
      return [...prev, { product, quantity: 1 }]
    })
    setAddedAnim(true)
    setTimeout(() => setAddedAnim(false), 1200)
  }

  function removeFromCart(id) {
    setCart(prev => prev.filter(i => i.product.id !== id))
  }

  function totalItems() {
    return cart.reduce((sum, i) => sum + i.quantity, 0)
  }

  function totalPrice() {
    return cart.reduce((sum, i) => sum + i.product.price_rub * i.quantity, 0)
  }

  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX
  }

  function handleTouchEnd(e, imagesLength) {
    if (touchStartX.current === null) return
    const diff = touchStartX.current - e.changedTouches[0].clientX
    if (Math.abs(diff) > 50) {
      if (diff > 0) setActiveImg(i => Math.min(i + 1, imagesLength - 1))
      else setActiveImg(i => Math.max(i - 1, 0))
    }
    touchStartX.current = null
  }

  // ─── КОРЗИНА ─────────────────────────────────────────────────────────────────
  if (cartOpen) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white font-sans pb-10">
        <div className="fixed top-0 w-full bg-[#0a0a0a]/90 backdrop-blur-md z-30 px-4 py-4 flex items-center gap-3 border-b border-white/5">
          <button
            onClick={() => setCartOpen(false)}
            className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center active:scale-90 transition-transform"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <h1 className="text-lg font-semibold">Корзина</h1>
          {totalItems() > 0 && (
            <span className="ml-auto text-sm text-zinc-400">{totalItems()} товар{totalItems() > 1 ? 'а' : ''}</span>
          )}
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
              <div className="flex flex-col gap-3 mb-6">
                {cart.map(({ product, quantity }) => (
                  <div key={product.id} className="bg-white/5 border border-white/5 rounded-2xl p-3 flex items-center gap-3">
                    <div className="w-16 h-16 bg-white rounded-xl flex-shrink-0">
                      <img
                        src={product.images?.[0]}
                        alt={product.name}
                        loading="lazy"
                        className="w-full h-full object-contain mix-blend-multiply p-1"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-zinc-400">{product.brand}</p>
                      <p className="text-sm font-medium leading-tight line-clamp-2 mt-0.5">{product.name}</p>
                      <p className="text-sm font-bold mt-1.5 text-white">
                        {(product.price_rub * quantity).toLocaleString('ru-RU')} ₽
                        {quantity > 1 && <span className="text-xs text-zinc-500 font-normal ml-2">x{quantity}</span>}
                      </p>
                    </div>
                    <button
                      onClick={() => removeFromCart(product.id)}
                      className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center flex-shrink-0 active:scale-90 transition-transform"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>

              <div className="bg-white/5 border border-white/5 rounded-2xl p-5 mb-6">
                <div className="flex justify-between text-sm text-zinc-400 mb-2">
                  <span>Товаров</span>
                  <span>{totalItems()} шт.</span>
                </div>
                <div className="flex justify-between font-bold text-lg text-white">
                  <span>Итого</span>
                  <span>{totalPrice().toLocaleString('ru-RU')} ₽</span>
                </div>
              </div>

              <button className="w-full bg-white text-black font-semibold py-4 rounded-2xl active:scale-[0.98] transition-transform text-base shadow-lg shadow-white/10">
                Оформить заказ
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  // ─── КАРТОЧКА ТОВАРА ──────────────────────────────────────────────────────────
  if (selected) {
    const images = selected.images || []
    return (
      <div className="min-h-screen bg-[#0a0a0a] text-white font-sans pb-10">
        <div className="fixed top-0 w-full bg-[#0a0a0a]/80 backdrop-blur-md z-30 px-4 py-4 flex items-center justify-between border-b border-white/5">
          <button
            onClick={() => setSelected(null)}
            className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center active:scale-90 transition-transform"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <button
            onClick={() => setCartOpen(true)}
            className="relative w-10 h-10 bg-white/10 rounded-full flex items-center justify-center active:scale-90 transition-transform"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" strokeLinecap="round" strokeLinejoin="round"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0" strokeLinecap="round"/>
            </svg>
            {totalItems() > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-white text-black text-[10px] font-bold w-4.5 h-4.5 px-1.5 py-0.5 rounded-full flex items-center justify-center animate-bounce">
                {totalItems()}
              </span>
            )}
          </button>
        </div>

        <div
          className="pt-20 px-4 pb-4 select-none"
          onTouchStart={handleTouchStart}
          onTouchEnd={(e) => handleTouchEnd(e, images.length)}
        >
          <div className="relative bg-white rounded-3xl aspect-[4/3] w-full flex items-center justify-center p-4 shadow-[0_0_30px_rgba(255,255,255,0.05)] overflow-hidden">
            <img
              key={activeImg}
              src={images[activeImg]}
              alt={selected.name}
              loading="lazy"
              className="w-full h-full object-contain mix-blend-multiply animate-fadeIn"
            />
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setActiveImg(i => Math.max(i - 1, 0))}
                  className={`absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/5 hover:bg-black/10 text-black rounded-full flex items-center justify-center transition-all duration-200 active:scale-90 ${activeImg === 0 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
                <button
                  onClick={() => setActiveImg(i => Math.min(i + 1, images.length - 1))}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/5 hover:bg-black/10 text-black rounded-full flex items-center justify-center transition-all duration-200 active:scale-90 ${activeImg === images.length - 1 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>

        {images.length > 1 && (
          <div className="flex gap-2 justify-center pb-4">
            {images.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveImg(i)}
                className={`h-1.5 rounded-full transition-all duration-300 ${i === activeImg ? 'bg-white w-6' : 'bg-white/20 w-1.5'}`}
              />
            ))}
          </div>
        )}

        <div className="px-5 pt-2">
          <p className="text-zinc-400 text-sm font-medium tracking-wide mb-1.5 uppercase">{selected.brand}</p>
          <h1 className="text-2xl font-semibold leading-tight mb-4 text-zinc-100">{selected.name}</h1>

          <div className="flex items-end gap-3 mb-6">
            <span className="text-3xl font-bold text-white tracking-tight">
              {selected.price_rub.toLocaleString('ru-RU')} ₽
            </span>
            {selected.original_price_eur && (
              <span className="text-lg text-zinc-500 line-through decoration-zinc-500/50 mb-0.5">
                {Math.round(selected.original_price_eur * (selected.price_rub / selected.price_eur)).toLocaleString('ru-RU')} ₽
              </span>
            )}
          </div>

          {selected.distance && (
            <div className="flex gap-2 flex-wrap mb-8">
              {selected.distance.split(',').map((d) => (
                <span key={d} className="bg-white/10 border border-white/5 text-zinc-200 text-xs font-medium px-4 py-2 rounded-full tracking-wide">
                  {d.trim()}
                </span>
              ))}
            </div>
          )}

          <div className="bg-white/5 border border-white/5 rounded-2xl p-5 mb-8 shadow-inner">
            <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-line font-light">
              {selected.description}
            </p>
          </div>

          <button
            onClick={() => addToCart(selected)}
            className={`w-full font-semibold text-base py-4 rounded-2xl transition-all duration-300 active:scale-[0.98] ${addedAnim ? 'bg-green-500 text-white shadow-[0_0_20px_rgba(34,197,94,0.4)]' : 'bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.1)]'}`}
          >
            {addedAnim ? '✓ Добавлено' : 'В корзину'}
          </button>
        </div>
      </div>
    )
  }

  // ─── КАТАЛОГ ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white pb-8 font-sans">
      <div className="sticky top-0 bg-[#0a0a0a]/90 backdrop-blur-md z-10 px-4 pt-5 pb-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold tracking-tight">Каталог</h1>
          <button
            onClick={() => setCartOpen(true)}
            className="relative w-10 h-10 bg-white/10 rounded-full flex items-center justify-center active:scale-90 transition-transform"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" strokeLinecap="round" strokeLinejoin="round"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0" strokeLinecap="round"/>
            </svg>
            {totalItems() > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-white text-black text-[10px] font-bold w-4.5 h-4.5 px-1.5 py-0.5 rounded-full flex items-center justify-center animate-bounce">
                {totalItems()}
              </span>
            )}
          </button>
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          {FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => setFilter(f.value)}
              className={`flex-shrink-0 px-5 py-2 rounded-full text-sm font-medium transition-all duration-200 active:scale-95 ${filter === f.value ? 'bg-white text-black' : 'bg-white/10 text-zinc-300'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 pt-5">
        {loading ? (
          <div className="grid grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white/5 rounded-2xl aspect-[3/4] overflow-hidden relative">
                <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} onClick={setSelected} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
