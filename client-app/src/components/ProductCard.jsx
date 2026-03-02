import { useState, useEffect } from 'react'

export default function ProductCard({ product, onClick }) {
  const [imgIndex, setImgIndex] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const images = product.images || []

  useEffect(() => {
    images.forEach(src => {
      const img = new Image()
      img.src = src
    })
  }, [])

  return (
    <div
      onClick={() => onClick(product)}
      className="bg-zinc-900 rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 active:scale-95 hover:scale-[1.02] hover:shadow-xl hover:shadow-black/50"
    >
      <div className="relative bg-white aspect-square flex items-center justify-center p-3">
        {!loaded && (
          <div className="absolute inset-0 bg-zinc-200 animate-pulse rounded-t-2xl" />
        )}
        {images.length > 0 ? (
          <img
            src={images[imgIndex]}
            alt={product.name}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            className={`w-full h-full object-contain transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
            onError={(e) => { e.target.src = 'https://placehold.co/300x300?text=No+Image' }}
          />
        ) : (
          <div className="text-zinc-400 text-xs">Нет фото</div>
        )}

        {product.original_price_eur && (
          <div className="absolute top-2 left-2 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow">
            -{Math.round((1 - product.price_eur / product.original_price_eur) * 100)}%
          </div>
        )}
      </div>

      {images.length > 1 && (
        <div className="flex gap-1.5 justify-center py-2 bg-zinc-900">
          {images.map((_, i) => (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); setImgIndex(i); setLoaded(false) }}
              className={`h-1.5 rounded-full transition-all duration-300 ${i === imgIndex ? 'bg-white w-4' : 'bg-zinc-600 w-1.5'}`}
            />
          ))}
        </div>
      )}

      <div className="px-3 pb-3 pt-1">
        <p className="text-zinc-400 text-xs">{product.brand}</p>
        <p className="text-white text-sm font-semibold leading-tight line-clamp-2 mt-0.5">{product.name}</p>
        <div className="mt-2">
          {product.original_price_eur && (
            <p className="text-zinc-500 text-xs line-through">
              {Math.round(product.original_price_eur * (product.price_rub / product.price_eur)).toLocaleString('ru-RU')} ₽
            </p>
          )}
          <p className="text-white font-bold text-base">{product.price_rub.toLocaleString('ru-RU')} ₽</p>
        </div>
      </div>
    </div>
  )
}
