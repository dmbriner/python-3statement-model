function normalizeBasePath(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed === "/") return "";
  return `/${trimmed.replace(/^\/+|\/+$/g, "")}`;
}

export const appName = process.env.NEXT_PUBLIC_APP_NAME?.trim() || "Tickr";
export const appBasePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH);

export function withBasePath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!appBasePath) {
    return normalizedPath;
  }
  if (normalizedPath === "/") {
    return appBasePath;
  }
  return `${appBasePath}${normalizedPath}`;
}

export function stripBasePath(pathname: string): string {
  if (!appBasePath) {
    return pathname || "/";
  }
  if (pathname === appBasePath) {
    return "/";
  }
  if (pathname.startsWith(`${appBasePath}/`)) {
    return pathname.slice(appBasePath.length);
  }
  return pathname || "/";
}
