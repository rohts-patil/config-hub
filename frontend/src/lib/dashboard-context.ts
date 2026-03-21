"use client";

const LAST_ORG_ID_STORAGE_KEY = "confighub:last-org-id";
const LAST_PRODUCT_ID_STORAGE_PREFIX = "confighub:last-product-id:";

export function getLastOrgId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(LAST_ORG_ID_STORAGE_KEY);
}

export function setLastOrgId(orgId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LAST_ORG_ID_STORAGE_KEY, orgId);
}

export function clearLastOrgId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LAST_ORG_ID_STORAGE_KEY);
}

export function getLastProductId(orgId: string) {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(
    `${LAST_PRODUCT_ID_STORAGE_PREFIX}${orgId}`
  );
}

export function setLastProductId(orgId: string, productId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    `${LAST_PRODUCT_ID_STORAGE_PREFIX}${orgId}`,
    productId
  );
}

export function clearLastProductId(orgId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(`${LAST_PRODUCT_ID_STORAGE_PREFIX}${orgId}`);
}
