export default function SeverityBadge({ severity }) {

  const colors = {
    critical: "bg-red-600",
    high: "bg-orange-500",
    medium: "bg-yellow-500",
    low: "bg-blue-500",
  };

  return (
    <span
      className={`
        px-3 py-1 rounded-full text-white text-sm font-semibold
        ${colors[severity] || "bg-gray-500"}
      `}
    >
      {severity}
    </span>
  );
}