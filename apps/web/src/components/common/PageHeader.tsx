import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

type PageHeaderProps = {
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2} mb={3}>
      <Box>
        <Typography variant="h4">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, maxWidth: 720 }}>
          {description}
        </Typography>
      </Box>
      {actions}
    </Stack>
  );
}
