import { useLocation } from "react-router-dom";
import { PageHeader } from "../../components/common/PageHeader";
import { findNavLeaf } from "../../navigation/navConfig";

export function WorkspacePage() {
  const { pathname } = useLocation();
  const leaf = findNavLeaf(pathname);

  return (
    <PageHeader
      title={leaf?.label ?? "Workspace"}
      description={
        leaf?.description ??
        "This module is part of the ufme review portal and will be implemented next."
      }
    />
  );
}
