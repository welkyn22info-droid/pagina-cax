import type { Metadata } from "next";
import ProveedorQuery from "@/componentes/ProveedorQuery";
import "./globals.css";

export const metadata: Metadata = {
  title: "Plataforma de riesgo",
  description: "Plataforma interna de riesgo — valoración, pasivo, funding ratio y cupos",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="antialiased">
        <ProveedorQuery>{children}</ProveedorQuery>
      </body>
    </html>
  );
}
