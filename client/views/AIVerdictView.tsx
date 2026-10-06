import React from 'react';

interface AIVerdictProps {
  verdict: string;
}

export const AIVerdictView: React.FC<AIVerdictProps> = ({ verdict }) => {
  return (
    <div className="spa-verdict-box">
      <div className="spa-verdict-title">
        <span>🤖</span>
        <span>Thẩm định giá thông minh (AI)</span>
      </div>
      <p className="spa-verdict-desc">
        {verdict || 'Đang phân tích và đối soát giá trên các sàn thương mại điện tử...'}
      </p>
    </div>
  );
};