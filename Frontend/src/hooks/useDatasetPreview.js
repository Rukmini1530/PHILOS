import { useEffect, useState } from "react";
import api, { API_BASE_URL } from "../services/api";

/** Load private previews through the authenticated API; demo previews stay public. */
export default function useDatasetPreview(dataset) {
  const cacheBust = dataset?.updated_at || dataset?.created_at || "";
  const resourceKey = dataset?.id
    ? `${dataset.id}:${dataset.is_demo}:${cacheBust}`
    : null;
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl = null;

    setPreview(null);
    if (!dataset?.id) return undefined;

    if (dataset.is_demo) {
      const version = cacheBust ? `?v=${encodeURIComponent(cacheBust)}` : "";
      setPreview({
        key: resourceKey,
        url: `${API_BASE_URL}/api/tiles/${dataset.id}/preview${version}`,
      });
      return undefined;
    }

    api
      .fetchDatasetPreview(dataset.id)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (!cancelled) setPreview({ key: resourceKey, url: objectUrl });
        else URL.revokeObjectURL(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setPreview({ key: resourceKey, url: null });
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [dataset?.id, dataset?.is_demo, cacheBust, resourceKey]);

  return preview?.key === resourceKey ? preview.url : null;
}
