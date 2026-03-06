import { useState, memo } from 'react'

const ProductCard = memo(function ProductCard({ product, onClick }) {
  const [imgIndex, setImgIndex] = useState(0)
  const [loaded, setLoaded]     = useState(false)
  const images   = product.images || []
  const distance = product.attributes?.distance

  return (
    <div
      onClick={() => onClick(product)}
      className="bg-[#1C1E24] border border-white/5 rounded-2xl overflow-hidden cursor-pointer transition-transform duration-150 active:scale-95"
      style={{ contain: 'layout style paint' }} // 🔑 изолирует перерисовку
    >
      <div className="relative bg-[#EBEBED] aspect-square flex items-center justify-center p-3">
        {!loaded && (
          <div className="absolute inset-0 bg-[#DDDDE0] animate-pulse rounded-t-2xl" />
        )}
        {images.length > 0 ? (
          <img
            src={images[imgIndex]}
            alt={product.name}
            loading="lazy"
            decoding="async" // 🔑 не блокирует main thread
            onLoad={() => setLoaded(true)}
            className={`w-full h-full object-contain mix-blend-multiply transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
            onError={(e) => { e.target.src = 'https://placehold.co/300x300?text=No+Image' }}
          />
        ) : (
          <div className="text-zinc-400 text-xs">Нет фото</div>
        )}

        {product.original_price_eur && (
          <div className="absolute top-2 left-2 bg-[#FF5A00] text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
            -{Math.round((1 - product.price_eur / product.original_price_eur) * 100)}%
          </div>
        )}
        {distance && (
          <div className="absolute top-2 right-2 bg-black/50 text-white text-[9px] font-bold px-2 py-0.5 rounded-full border border-white/10">
            {distance}
          </div>
        )}
      </div>

      {images.length > 1 && (
        <div className="flex gap-1.5 justify-center py-2 bg-[#1C1E24]">
          {images.map((_, i) => (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); setImgIndex(i); setLoaded(false) }}
              className={`h-1.5 rounded-full transition-all duration-300 ${i === imgIndex ? 'bg-[#FF5A00] w-4' : 'bg-white/20 w-1.5'}`}
            />
          ))}
        </div>
      )}

      <div className="px-3 pb-3 pt-1">
        <p className="text-[#888] text-xs font-medium">{product.brand}</p>
        <p className="text-white text-sm font-semibold leading-tight line-clamp-2 mt-0.5">{product.name}</p>
        <div className="mt-2">
          {product.original_price_eur && (
            <p className="text-zinc-600 text-xs line-through">
              {Math.round(product.original_price_eur * (product.price_rub / product.price_eur)).toLocaleString('ru-RU')} ₽
            </p>
          )}
          <p className="text-white font-extrabold text-lg tracking-tight leading-none mt-0.5">
            {product.price_rub.toLocaleString('ru-RU')} ₽
          </p>
        </div>
      </div>
    </div>
  )
})

export default ProductCard
