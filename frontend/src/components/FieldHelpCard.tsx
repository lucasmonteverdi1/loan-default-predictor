import { FIELD_HELP } from "../fieldHelp";

export default function FieldHelpCard({ onClose }: { onClose: () => void }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">What do these fields mean?</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close field descriptions"
          className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          ✕
        </button>
      </div>
      <dl className="flex flex-col gap-3">
        {FIELD_HELP.map(({ label, help }) => (
          <div key={label}>
            <dt className="text-xs font-semibold text-gray-700">{label}</dt>
            <dd className="text-xs text-gray-500">{help}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
