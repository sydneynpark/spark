import { useEffect } from 'react';

export const SITE_TITLE = "Sydney's wiki";

// Sets the browser tab title to "<title> | Sydney's wiki", or just the site
// title when `title` is empty (e.g. the home page, or a page still loading).
export function usePageTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} | ${SITE_TITLE}` : SITE_TITLE;
  }, [title]);
}
