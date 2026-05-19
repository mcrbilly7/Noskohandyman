import React, { useState } from "react";
import FileUploader from "./FileUploader";

/** Inline W9 signing form: typed signature + optional PDF upload. */
export default function W9Signer({ onSubmit, busy = false }) {
  const [form, setForm] = useState({
    full_legal_name: "",
    business_name: "",
    ssn_or_ein: "",
    address: "",
    tax_classification: "individual",
    typed_signature: "",
    pdf_path: "",
  });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = (e) => {
    e.preventDefault();
    onSubmit?.(form);
  };
  return (
    <form onSubmit={submit} className="grid gap-4" data-testid="w9-form">
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="overline">Full legal name *</label>
          <input data-testid="w9-name" required value={form.full_legal_name} onChange={set("full_legal_name")} />
        </div>
        <div>
          <label className="overline">Business name (optional)</label>
          <input data-testid="w9-business" value={form.business_name} onChange={set("business_name")} />
        </div>
      </div>
      <div>
        <label className="overline">Tax classification *</label>
        <select data-testid="w9-classification" value={form.tax_classification} onChange={set("tax_classification")}>
          <option value="individual">Individual / Sole proprietor</option>
          <option value="llc">LLC</option>
          <option value="c-corp">C-Corp</option>
          <option value="s-corp">S-Corp</option>
          <option value="partnership">Partnership</option>
        </select>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="overline">SSN or EIN *</label>
          <input data-testid="w9-tin" required value={form.ssn_or_ein} onChange={set("ssn_or_ein")} placeholder="XXX-XX-XXXX" />
        </div>
        <div>
          <label className="overline">Mailing address *</label>
          <input data-testid="w9-address" required value={form.address} onChange={set("address")} />
        </div>
      </div>
      <div>
        <label className="overline">Type your signature *</label>
        <input
          data-testid="w9-signature"
          required
          value={form.typed_signature}
          onChange={set("typed_signature")}
          placeholder="Type your full name as signature"
          style={{ fontFamily: "'Cabinet Grotesk', cursive", fontSize: "1.25rem" }}
        />
        <p className="text-xs text-neutral-600 mt-1">
          By typing my name above, I certify the information is correct under penalty of perjury.
        </p>
      </div>
      <div>
        <label className="overline">Upload completed W9 PDF (optional)</label>
        <FileUploader
          folder="w9"
          accept="application/pdf"
          multiple={false}
          value={form.pdf_path ? [form.pdf_path] : []}
          onChange={(arr) => setForm({ ...form, pdf_path: arr[0] || "" })}
          testid="w9-pdf-uploader"
        />
      </div>
      <button type="submit" className="btn-brutal dark" disabled={busy} data-testid="w9-submit-btn">
        {busy ? "Signing…" : "Sign W9 & Continue"}
      </button>
    </form>
  );
}
