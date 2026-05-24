import SeverityBadge from "./SeverityBadge";

export default function ReviewCard({ issue }) {

  const suggestion =
    typeof issue.suggestion === "string"
      ? issue.suggestion
      : issue.suggestion?.text ||
        "No suggestion provided";

  const vulnerableCode =
    issue.vulnerable_code ||
    issue.vulnerableCode ||
    "No vulnerable code provided";

  const fixedCode =
    issue.fixed_code ||
    issue.fixedCode ||
    "No fix provided";

  return (
    <div className="bg-white rounded-xl shadow-md p-5 mb-4 border">

      <p className="text-sm font-semibold text-gray-500 font-mono mb-2">
        {issue.file || "pasted-code"}
      </p>

      <div className="flex items-center justify-between mb-3">

        <h2 className="text-lg font-semibold">
          {issue.category || "quality"}
        </h2>

        <SeverityBadge severity={issue.severity || "medium"} />

      </div>

      <p className="text-gray-800 mb-3">
        {issue.message || "Issue detected"}
      </p>

      <div className="bg-gray-100 p-3 rounded-lg">

        <p className="text-sm font-medium text-gray-700">
          Suggestion
        </p>

        <p className="text-gray-800 mt-1">
          {suggestion}
        </p>

      </div>

      <div className="mt-4">

        <p className="font-semibold mb-2">
          Vulnerable Code
        </p>

        <pre className="
          bg-red-100
          p-3
          rounded-lg
          overflow-x-auto
          text-sm
          whitespace-pre-wrap
        ">
          <code>{vulnerableCode}</code>
        </pre>

      </div>

      <div className="mt-4">

        <p className="font-semibold mb-2">
          Recommended Fix
        </p>

        <pre className="
          bg-green-100
          p-3
          rounded-lg
          overflow-x-auto
          text-sm
          whitespace-pre-wrap
        ">
          <code>{fixedCode}</code>
        </pre>

      </div>

    </div>
  );
}
