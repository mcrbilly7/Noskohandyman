import React, { useState } from "react";
import { api } from "@/lib/api";
import { UploadCloud, X, Loader2 } from "lucide-react";

/** Uploads files via /api/upload and returns list of storage paths. */
export default function FileUploader({ folder = "misc", multiple = true, accept = "image/*", onChange, value = [], testid = "file-uploader" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const handleFiles = async (files) => {
    setError(null);
    setBusy(true);
    try {
      const uploaded = [];
      for (const f of files) {
        const fd = new FormData();
        fd.append("file", f);
        fd.append("folder", folder);
        const res = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
        uploaded.push(res.data.path);
      }
      onChange?.([...(value || []), ...uploaded]);
    } catch (e) {
      setError(e?.response?.data?.detail || "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = (idx) => {
    const next = [...value];
    next.splice(idx, 1);
    onChange?.(next);
  };

  return (
    <div data-testid={testid}>
      <label className="dropzone flex flex-col items-center justify-center text-center cursor-pointer">
        {busy ? <Loader2 className="w-6 h-6 animate-spin" /> : <UploadCloud className="w-6 h-6" />}
        <div className="overline mt-2">{busy ? "Uploading…" : "Drop or click to upload"}</div>
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(e) => handleFiles(Array.from(e.target.files || []))}
          data-testid={`${testid}-input`}
        />
      </label>
      {error && <div className="text-red-600 text-sm mt-2">{error}</div>}
      {value?.length > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {value.map((p, i) => (
            <div key={i} className="relative border border-black aspect-square overflow-hidden">
              {accept.includes("image") ? (
                <img src={`${process.env.REACT_APP_BACKEND_URL}/api/files/${p}`} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="p-2 text-xs break-all">{p.split("/").pop()}</div>
              )}
              <button
                type="button"
                onClick={() => remove(i)}
                className="absolute top-1 right-1 bg-black text-white p-1"
                data-testid={`${testid}-remove-${i}`}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
