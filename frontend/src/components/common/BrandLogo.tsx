import React from 'react';
import cyborgsLogo from './cyborgs-logo.svg';

interface BrandLogoProps {
  className?: string;
  alt?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  className = '',
  alt = 'Cyborgs security logo'
}) => {
  return <img src={cyborgsLogo} alt={alt} className={className} />;
};
