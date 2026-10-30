import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

type PageHeaderProps = {
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "flex-end" }} gap={3} mb={2}>
      <Box sx={{ minWidth: 0, maxWidth: 820 }}>
        <Typography variant="h4" component="h1" sx={{ fontSize: "clamp(36px, 4vw, 56px)" }}>
          {title}
        </Typography>
        <Typography sx={{ mt: 1.5, fontSize: 17, lineHeight: 1.45, color: "text.secondary", maxWidth: 680 }}>{description}</Typography>
      </Box>
      {actions ? <Stack direction="row" gap={1.5} flexWrap="wrap">{actions}</Stack> : null}
    </Stack>
  );
}
