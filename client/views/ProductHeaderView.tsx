import React from 'react';
import type { CanonicalEntity } from '../models/analyze_dto';

interface ProductHeaderProps {
  entity: CanonicalEntity;
  rawPrice?: number;
  imageUrl?: string;
  onRefresh: () => void;
  isLoading: boolean;
}

export const ProductHeaderView: React.FC<ProductHeaderProps> = ({
  entity,
  rawPrice,
  imageUrl,
  onRefresh,
  isLoading
}) => {
  const displayPrice = entity.normalized_price || rawPrice;

  return (
    <div className="spa-product-header">
      <div className="spa-product-row">
        {imageUrl ? (
          <img src={imageUrl} alt={entity.model} className="spa-product-img" />
        ) : (
          <div className="spa-product-img" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px' }}>
            📦
          </div>
        )}

        <div className="spa-product-meta">
          <div className="spa-tag-row">
            {entity.brand && <span className="spa-brand-tag">{entity.brand}</span>}
          </div>

          <h2 className="spa-product-title" title={entity.model}>
            {entity.model || 'Sản phẩm đang chọn'}
          </h2>

          <div>
            <span className="spa-price-label">Giá hiện tại:</span>
            <span className="spa-price-val">
              {displayPrice ? `${displayPrice.toLocaleString('vi-VN')} ₫` : 'Chưa có giá'}
            </span>
          </div>
        </div>
      </div>

      <button onClick={onRefresh} disabled={isLoading} className="spa-btn-refresh">
        <span>🔄</span>
        <span>{isLoading ? 'Đang phân tích dữ liệu...' : 'Làm mới / Quét lại'}</span>
      </button>
    </div>
  );
};