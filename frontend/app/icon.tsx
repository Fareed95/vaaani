import { ImageResponse } from "next/og";

export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#173225",
          borderRadius: 16,
          fontFamily: "Georgia, serif",
        }}
      >
        <div
          style={{
            display: "flex",
            width: 48,
            height: 48,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: "14px 14px 14px 6px",
            background:
              "radial-gradient(circle at 34% 22%, rgba(201,144,47,0.55), transparent 60%), #173225",
            color: "#f8ba3c",
            fontSize: 30,
            fontWeight: 700,
            transform: "rotate(-5deg)",
          }}
        >
          वा
        </div>
      </div>
    ),
    { ...size },
  );
}
